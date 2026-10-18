import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  startFocusSession,
  getActiveFocusSession,
  updateFocusSession,
  isAuthenticated,
  loginUser,
  registerUser,
  getCurrentUser,
  logoutUser,
  clearAuth,
  getTodayStats,
  getRecentActivity,
  getGoals,
  createGoal,
  updateGoal,
  updateSettings,
  getSettings,
  SESSION_EXPIRED_EVENT,
  getRangeStats,
  getFocusSessions,
  updateProfile,
  deleteMyData,
  deleteGoal,
} from './lib/api'

const navItems = [
  { label: 'Today', icon: '◉' },
  { label: 'Focus', icon: '◷' },
  { label: 'Apps', icon: '▤' },
  { label: 'Stats', icon: '▥' },
  { label: 'Goals', icon: '⚑' },
  { label: 'Settings', icon: '⚙' },
]

const durations = [15, 25, 45, 60]

const focusScenes = [
  { id: 'zen', label: '☀ Zen' },
  { id: 'nature', label: '🌿 Nature' },
  { id: 'night', label: '☾ Night' },
]

function formatTime(seconds) {
  const safeSeconds = Math.max(0, seconds)
  const minutes = Math.floor(safeSeconds / 60)
  const remainingSeconds = safeSeconds % 60

  return `${String(minutes).padStart(2, '0')}:${String(
    remainingSeconds,
  ).padStart(2, '0')}`
}

function formatMinutes(seconds) {
  const minutes = Math.max(0, Math.floor((seconds || 0) / 60))
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60

  if (hours === 0) return `${remainingMinutes}m`
  return `${hours}h ${String(remainingMinutes).padStart(2, '0')}m`
}

function getTodayDate() {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function dateString(offsetDays = 0) {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function AmbientCreatures() {
  return (
    <div className="ambient-creatures" aria-hidden="true">
      {Array.from({ length: 12 }, (_, i) => (
        <span
          key={`firefly-${i}`}
          className="firefly"
          style={{
            left: `${(i * 29 + 7) % 96}%`,
            top: `${(i * 37 + 13) % 90}%`,
            animationDelay: `${(i * 1.7) % 9}s`,
            animationDuration: `${12 + (i % 5) * 3}s`,
          }}
        />
      ))}

      {Array.from({ length: 7 }, (_, i) => (
        <span
          key={`bug-${i}`}
          className="flying-bug"
          style={{
            left: `${(i * 31 + 11) % 92}%`,
            top: `${(i * 23 + 19) % 85}%`,
            animationDelay: `${i * 2.1}s`,
            animationDuration: `${10 + (i % 4) * 3}s`,
          }}
        >
          <span className="bug-spots" />
        </span>
      ))}
    </div>
  )
}

function App() {
  const [activePage, setActivePage] = useState('Today')
  const [theme, setTheme] = useState('light')
  const [focusMode, setFocusMode] = useState(false)
  const [focusScene, setFocusScene] = useState('zen')

  const [duration, setDuration] = useState(25)
  const [remaining, setRemaining] = useState(25 * 60)
  const [running, setRunning] = useState(false)
  const [sessionActive, setSessionActive] = useState(false)
  const [focusSessionId, setFocusSessionId] = useState(null)
  const [sessionError, setSessionError] = useState('')
  const [sessionCount, setSessionCount] = useState(0)
  const [sessionBusy, setSessionBusy] = useState(false)

  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [authName, setAuthName] = useState('')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [authBusy, setAuthBusy] = useState(false)

  const [todayStats, setTodayStats] = useState(null)
  const [recentActivity, setRecentActivity] = useState([])
  const [goals, setGoals] = useState([])
  const [settings, setSettings] = useState(null)
  const [dataError, setDataError] = useState('')
  const [loadingData, setLoadingData] = useState(false)
  const [newGoalType, setNewGoalType] = useState('daily_focus_min')
  const [newGoalTarget, setNewGoalTarget] = useState('60')
  const [newGoalApp, setNewGoalApp] = useState('')
  const [goalError, setGoalError] = useState('')
  const [settingsMessage, setSettingsMessage] = useState('')

  const [rangeDays, setRangeDays] = useState(7)
  const [rangeStats, setRangeStats] = useState(null)
  const [rangeError, setRangeError] = useState('')
  const [focusHistory, setFocusHistory] = useState([])
  const [profileName, setProfileName] = useState('')
  const [profileMessage, setProfileMessage] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleteMessage, setDeleteMessage] = useState('')

  // Electron desktop-agent integration.
  const [agentStatus, setAgentStatus] = useState({
    supported: Boolean(window.attentionDesktop?.isDesktopApp),
    running: false,
    backendReachable: false,
    checking: true,
    busy: false,
    error: '',
  })

  const completionRequestRef = useRef(null)

  async function refreshAgentStatus() {
    const desktop = window.attentionDesktop

    if (!desktop?.isDesktopApp) {
      setAgentStatus((previous) => ({
        ...previous,
        supported: false,
        checking: false,
      }))
      return
    }

    try {
      const result = await desktop.getAgentStatus()

      setAgentStatus((previous) => ({
        ...previous,
        ...result,
        checking: false,
        error: result.error || '',
      }))
    } catch (error) {
      setAgentStatus((previous) => ({
        ...previous,
        checking: false,
        error: error.message || 'Could not read desktop-agent status.',
      }))
    }
  }

  async function handleAgentAction(action) {
    const desktop = window.attentionDesktop

    if (!desktop?.isDesktopApp || agentStatus.busy) return

    setAgentStatus((previous) => ({
      ...previous,
      busy: true,
      error: '',
    }))

    try {
      const result =
        action === 'start'
          ? await desktop.startAgent()
          : await desktop.stopAgent()

      setAgentStatus((previous) => ({
        ...previous,
        ...result,
        checking: false,
        busy: false,
        error: result.error || '',
      }))

      // Read the actual process status after the operation.
      await refreshAgentStatus()
    } catch (error) {
      setAgentStatus((previous) => ({
        ...previous,
        checking: false,
        busy: false,
        error: error.message || 'Agent operation failed.',
      }))
    }
  }

  // Check desktop-agent status periodically while the app is open.
  useEffect(() => {
    const desktop = window.attentionDesktop

    if (!desktop?.isDesktopApp) {
      setAgentStatus((previous) => ({
        ...previous,
        supported: false,
        checking: false,
      }))
      return undefined
    }

    let cancelled = false

    async function checkStatus() {
      try {
        const result = await desktop.getAgentStatus()

        if (!cancelled) {
          setAgentStatus((previous) => ({
            ...previous,
            ...result,
            checking: false,
            error: result.error || '',
          }))
        }
      } catch (error) {
        if (!cancelled) {
          setAgentStatus((previous) => ({
            ...previous,
            checking: false,
            error: error.message || 'Could not read agent status.',
          }))
        }
      }
    }

    checkStatus()

    const intervalId = window.setInterval(checkStatus, 3000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  // When the API client reports that the session is really over, return to login.
  useEffect(() => {
    function onExpired() {
      setUser(null)
      setFocusSessionId(null)
      setSessionActive(false)
      setRunning(false)
      setAuthError('Your session expired. Please sign in again.')
    }

    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  // Restore authentication and any active backend focus session.
  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      if (!isAuthenticated()) {
        setAuthReady(true)
        return
      }

      try {
        const profile = await getCurrentUser()
        if (cancelled) return

        setUser(profile)

        const active = await getActiveFocusSession()
        if (cancelled || !active) return

        setFocusSessionId(active.id)
        setDuration(active.planned_min)
        setSessionActive(true)
        setSessionCount((count) => count + 1)

        if (active.status === 'running') {
          const elapsed = Math.floor(
            (Date.now() - new Date(active.started_at).getTime()) / 1000,
          )

          const restoredRemaining = Math.max(
            0,
            active.planned_min * 60 - elapsed,
          )

          setRemaining(restoredRemaining)

          if (restoredRemaining > 0) {
            await updateFocusSession(active.id, 'pause')
          }

          if (!cancelled && restoredRemaining === 0) {
            await updateFocusSession(active.id, 'stop')
            setFocusSessionId(null)
            setSessionActive(false)
          }
        } else {
          setRemaining(active.planned_min * 60)
        }
      } catch (error) {
        // Only a real 401 means the login is gone. A network error or a busy
        // server must not log the user out.
        if (error.status === 401) clearAuth()

        if (!cancelled) {
          setUser(null)
          setAuthError(error.message || 'Could not restore your session.')
        }
      } finally {
        if (!cancelled) setAuthReady(true)
      }
    }

    bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  // Countdown runs only while the focus session is running.
  useEffect(() => {
    if (!running) return undefined

    const interval = window.setInterval(() => {
      setRemaining((previous) => Math.max(0, previous - 1))
    }, 1000)

    return () => window.clearInterval(interval)
  }, [running])

  // Persist completion when the countdown reaches zero.
  useEffect(() => {
    if (
      remaining !== 0 ||
      !sessionActive ||
      !focusSessionId ||
      completionRequestRef.current === focusSessionId
    ) {
      return
    }

    const completedId = focusSessionId
    completionRequestRef.current = completedId
    setRunning(false)
    setSessionError('')

    let cancelled = false

    async function completeSession() {
      try {
        await updateFocusSession(completedId, 'stop')

        if (!cancelled) {
          setSessionActive(false)
          setFocusSessionId(null)
        }
      } catch (error) {
        if (!cancelled) {
          setSessionError(
            error.message || 'Could not save the completed focus session.',
          )
          completionRequestRef.current = null
        }
      }
    }

    completeSession()

    return () => {
      cancelled = true
    }
  }, [remaining, sessionActive, focusSessionId])

  // Load actual backend data after authentication.
  useEffect(() => {
    if (!user) return undefined

    let cancelled = false

    async function loadDashboard() {
      setLoadingData(true)
      setDataError('')

      const results = await Promise.allSettled([
        getTodayStats(),
        getRecentActivity(20),
        getGoals(false),
        getSettings(),
      ])

      if (cancelled) return

      const [statsResult, activityResult, goalsResult, settingsResult] = results

      if (statsResult.status === 'fulfilled') {
        setTodayStats(statsResult.value)
      } else {
        setDataError(statsResult.reason?.message || 'Could not load statistics.')
      }

      if (activityResult.status === 'fulfilled') {
        setRecentActivity(activityResult.value || [])
      }

      if (goalsResult.status === 'fulfilled') {
        setGoals(goalsResult.value || [])
      }

      if (settingsResult.status === 'fulfilled') {
        setSettings(settingsResult.value)
        setTheme(settingsResult.value.theme || 'light')
      }

      setLoadingData(false)
    }

    loadDashboard()

    return () => {
      cancelled = true
    }
  }, [user])

  // The desktop agent uploads every ~30 seconds, so refresh the live numbers too.
  useEffect(() => {
    if (!user) return undefined

    const intervalId = window.setInterval(async () => {
      try {
        const [stats, activity] = await Promise.all([
          getTodayStats(),
          getRecentActivity(20),
        ])
        setTodayStats(stats)
        setRecentActivity(activity || [])
      } catch {
        // The next tick retries; errors here should not disturb the UI.
      }
    }, 30000)

    return () => window.clearInterval(intervalId)
  }, [user])

  // Keep the profile form in sync with the logged-in user.
  useEffect(() => {
    if (user) setProfileName(user.name || '')
  }, [user])

  // Daily history for the Stats page (7 or 30 days).
  useEffect(() => {
    if (!user || activePage !== 'Stats') return undefined

    let cancelled = false
    setRangeError('')

    getRangeStats(dateString(-(rangeDays - 1)), dateString(0))
      .then((data) => {
        if (!cancelled) setRangeStats(data)
      })
      .catch((error) => {
        if (!cancelled) {
          setRangeError(error.message || 'Could not load history.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [user, activePage, rangeDays])

  // Past focus sessions for the Focus page (reloads when a session starts/ends).
  useEffect(() => {
    if (!user || activePage !== 'Focus') return undefined

    let cancelled = false

    getFocusSessions(10, 0)
      .then((data) => {
        if (!cancelled) setFocusHistory(data || [])
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [user, activePage, sessionActive])

  async function handleAuthSubmit(event) {
    event.preventDefault()
    setAuthError('')
    setAuthBusy(true)

    try {
      if (authMode === 'register') {
        await registerUser({
          name: authName.trim(),
          email: authEmail.trim(),
          password: authPassword,
        })
      }

      await loginUser({
        email: authEmail.trim(),
        password: authPassword,
      })

      // The desktop agent keeps its own login (separate tokens in the OS keyring).
      // Best effort: a failure here must not block the web login.
      if (window.attentionDesktop?.isDesktopApp) {
        window.attentionDesktop
          .loginAgent({ email: authEmail.trim(), password: authPassword })
          .then((result) => {
            if (!result?.ok) {
              setAgentStatus((previous) => ({
                ...previous,
                error: result?.error || 'Desktop agent login failed.',
              }))
            }
          })
          .catch(() => {})
      }

      const profile = await getCurrentUser()
      setUser(profile)
      setAuthPassword('')
    } catch (error) {
      setAuthError(error.message || 'Authentication failed.')
    } finally {
      setAuthBusy(false)
    }
  }

  async function handleLogout() {
    setAuthBusy(true)

    try {
      // Stop the agent first so it can do its final upload while the token is valid.
      if (agentStatus.supported && agentStatus.running) {
        await handleAgentAction('stop')
      }

      try {
        await window.attentionDesktop?.logoutAgent?.()
      } catch {
        // Agent logout is best effort.
      }

      await logoutUser()
    } catch {
      clearAuth()
    } finally {
      setUser(null)
      setFocusSessionId(null)
      setSessionActive(false)
      setRunning(false)
      setRemaining(duration * 60)
      setSessionError('')
      setTodayStats(null)
      setRangeStats(null)
      setFocusHistory([])
      setRecentActivity([])
      setGoals([])
      setSettings(null)
      setAuthBusy(false)
    }
  }

  async function startSession() {
    if (sessionBusy) return

    setSessionError('')

    if (!isAuthenticated()) {
      setSessionError('Please sign in to save your focus session.')
      return
    }

    setSessionBusy(true)

    try {
      if (sessionActive && focusSessionId) {
        if (!running) {
          await updateFocusSession(focusSessionId, 'resume')
          setRunning(true)
        }

        setActivePage('Focus')
        return
      }

      const session = await startFocusSession(duration, 'Focus session')

      completionRequestRef.current = null
      setFocusSessionId(session.id)
      setRemaining(duration * 60)
      setSessionActive(true)
      setSessionCount((count) => count + 1)
      setActivePage('Focus')
      setRunning(true)
    } catch (error) {
      setSessionError(error.message || 'Could not start focus session.')
    } finally {
      setSessionBusy(false)
    }
  }

  async function togglePause() {
    if (sessionBusy || !focusSessionId) {
      if (!focusSessionId) {
        setSessionError('No connected focus session was found.')
      }
      return
    }

    setSessionError('')
    setSessionBusy(true)

    try {
      const action = running ? 'pause' : 'resume'
      await updateFocusSession(focusSessionId, action)
      setRunning(!running)
    } catch (error) {
      setSessionError(error.message || 'Could not update focus session.')
    } finally {
      setSessionBusy(false)
    }
  }

  async function stopSession() {
    if (sessionBusy) return

    setSessionError('')
    setSessionBusy(true)

    try {
      if (focusSessionId) {
        await updateFocusSession(focusSessionId, 'stop')
      }

      completionRequestRef.current = null
      setRunning(false)
      setSessionActive(false)
      setFocusSessionId(null)
      setRemaining(duration * 60)
    } catch (error) {
      setSessionError(error.message || 'Could not stop focus session.')
    } finally {
      setSessionBusy(false)
    }
  }

  function changeDuration(value) {
    if (sessionActive || sessionBusy) return

    setDuration(value)
    setRemaining(value * 60)
    setSessionError('')
  }

  function navigateTo(page) {
    setActivePage(page)
    setFocusMode(false)
  }

  async function handleCreateGoal(event) {
    event.preventDefault()
    setGoalError('')

    const target = Number(newGoalTarget)

    if (!Number.isInteger(target) || target < 1) {
      setGoalError('Enter a valid positive target.')
      return
    }

    try {
      const body = {
        type: newGoalType,
        target_value: target,
      }

      if (newGoalType === 'max_app_min') {
        if (!newGoalApp.trim()) {
          setGoalError('Enter an application name for this goal.')
          return
        }

        body.app_name = newGoalApp.trim()
      }

      const created = await createGoal(body)
      setGoals((current) => [...current, created])
      setNewGoalTarget('60')
      setNewGoalApp('')
    } catch (error) {
      setGoalError(error.message || 'Could not create goal.')
    }
  }

  async function handleToggleGoal(goal) {
    try {
      const updated = await updateGoal(goal.id, {
        is_active: !goal.is_active,
      })

      setGoals((current) =>
        current.map((item) => item.id === goal.id ? updated : item),
      )
    } catch (error) {
      setGoalError(error.message || 'Could not update goal.')
    }
  }

  async function handleSaveSettings(event) {
    event.preventDefault()
    if (!settings) return

    setSettingsMessage('')

    try {
      const updated = await updateSettings({
        theme,
        daily_focus_goal_min: Number(settings.daily_focus_goal_min),
        idle_threshold_sec: Number(settings.idle_threshold_sec),
        store_window_titles: settings.store_window_titles,
        ignored_apps: settings.ignored_apps,
        timezone: settings.timezone,
      })

      setSettings(updated)
      setSettingsMessage('Settings saved successfully.')
    } catch (error) {
      setSettingsMessage(error.message || 'Could not save settings.')
    }
  }

  async function handleSaveProfile(event) {
    event.preventDefault()
    setProfileMessage('')

    const name = profileName.trim()
    if (!name) {
      setProfileMessage('Name cannot be empty.')
      return
    }

    try {
      const updated = await updateProfile({ name })
      setUser(updated)
      setProfileMessage('Name updated.')
    } catch (error) {
      setProfileMessage(error.message || 'Could not update your name.')
    }
  }

  async function handleDeleteGoal(goal) {
    if (!window.confirm('Delete this goal?')) return

    try {
      await deleteGoal(goal.id)
      setGoals((current) => current.filter((item) => item.id !== goal.id))
    } catch (error) {
      setGoalError(error.message || 'Could not delete goal.')
    }
  }

  async function handleDeleteData(event) {
    event.preventDefault()
    if (deleteConfirm !== 'DELETE') return

    setDeleteMessage('')

    try {
      const result = await deleteMyData()
      const total = Object.values(result?.deleted || {}).reduce(
        (sum, count) => sum + Number(count || 0),
        0,
      )

      // Any running focus session may be gone now.
      setRunning(false)
      setSessionActive(false)
      setFocusSessionId(null)
      setRemaining(duration * 60)
      setRangeStats(null)
      setFocusHistory([])
      setDeleteConfirm('')

      // Reload what is left instead of guessing which tables were cleared.
      const [stats, activity, goalList] = await Promise.allSettled([
        getTodayStats(),
        getRecentActivity(20),
        getGoals(false),
      ])
      if (stats.status === 'fulfilled') setTodayStats(stats.value)
      if (activity.status === 'fulfilled') setRecentActivity(activity.value || [])
      if (goalList.status === 'fulfilled') setGoals(goalList.value || [])

      setDeleteMessage(`Deleted ${total} record(s).`)
    } catch (error) {
      setDeleteMessage(error.message || 'Could not delete your data.')
    }
  }

  if (!authReady) {
    return (
      <main className={`app-shell theme-${theme}`}>
        <section className="panel placeholder-panel">
          <h2>Loading your workspace...</h2>
        </section>
      </main>
    )
  }

  if (!user) {
    return (
      <main className={`app-shell theme-${theme}`}>
        <AmbientCreatures />

        <section
          className="panel placeholder-panel"
          style={{ maxWidth: 440, margin: '10vh auto', padding: 32 }}
        >
          <div className="eyebrow">ATTENTION PLATFORM</div>
          <h1>{authMode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
          <p>Sign in to save and sync your focus sessions.</p>

          <form onSubmit={handleAuthSubmit}>
            {authMode === 'register' && (
              <input
                value={authName}
                onChange={(event) => setAuthName(event.target.value)}
                placeholder="Your name"
                autoComplete="name"
                required
                maxLength={100}
              />
            )}

            <input
              type="email"
              value={authEmail}
              onChange={(event) => setAuthEmail(event.target.value)}
              placeholder="Email address"
              autoComplete="email"
              required
            />

            <input
              type="password"
              value={authPassword}
              onChange={(event) => setAuthPassword(event.target.value)}
              placeholder="Password"
              autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              required
            />

            {authMode === 'register' && (
              <p className="demo-note">
                Password must include an uppercase letter, lowercase letter,
                and number.
              </p>
            )}

            {authError && <p role="alert">{authError}</p>}

            <button className="primary-button" type="submit" disabled={authBusy}>
              {authBusy
                ? 'Please wait...'
                : authMode === 'login'
                  ? 'Sign in'
                  : 'Create account'}
            </button>
          </form>

          <button
            className="secondary-button"
            type="button"
            disabled={authBusy}
            onClick={() => {
              setAuthMode((mode) => mode === 'login' ? 'register' : 'login')
              setAuthError('')
            }}
          >
            {authMode === 'login'
              ? 'Create a new account'
              : 'Already have an account? Sign in'}
          </button>
        </section>
      </main>
    )
  }

  const screenTime = todayStats?.screen_time_sec ?? 0
  const focusTime = todayStats?.focus_sec ?? 0
  const taskSwitches = todayStats?.task_switches ?? 0
  const dailyGoal = settings?.daily_focus_goal_min ?? 180
  const goalPercent = Math.min(
    100,
    dailyGoal > 0 ? (focusTime / (dailyGoal * 60)) * 100 : 0,
  )
  const topApps = todayStats?.top_apps || []
  const timeline = todayStats?.timeline || []

  return (
    <main className={`app-shell theme-${theme} ${focusMode ? 'focus-mode' : ''}`}>
      <AmbientCreatures />

      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">◉</span>
          <span>Attention<span className="brand-light">.</span></span>
        </div>

        {/* Integrated desktop-agent status and controls */}
        <div className="tracking-status">
          <span
            className={`status-dot ${
              agentStatus.running ? 'agent-running' : 'agent-stopped'
            }`}
          />

          <span>
            {!agentStatus.supported
              ? 'Desktop app required'
              : agentStatus.checking
                ? 'Checking agent...'
                : agentStatus.running
                  ? 'Desktop agent running'
                  : 'Desktop agent stopped'}
          </span>

          {agentStatus.supported && (
            <button
              type="button"
              className="agent-control-button"
              disabled={agentStatus.busy || agentStatus.checking}
              onClick={() =>
                handleAgentAction(agentStatus.running ? 'stop' : 'start')
              }
            >
              {agentStatus.busy
                ? 'Please wait...'
                : agentStatus.running
                  ? 'Stop Agent'
                  : 'Start Agent'}
            </button>
          )}

          {agentStatus.supported && (
            <span className="agent-backend-status">
              {agentStatus.backendReachable ? 'API online' : 'API offline'}
            </span>
          )}
        </div>

        {agentStatus.error && (
          <p className="agent-error" role="status">
            {agentStatus.error}
          </p>
        )}

        <div className="topbar-right">
          <span className="topbar-caption">
            {user.name || user.email || 'Attention Workspace'}
          </span>

          <button
            className="icon-button"
            aria-label={focusMode ? 'Exit focus environment' : 'Enter focus environment'}
            title={focusMode ? 'Exit focus environment' : 'Enter focus environment'}
            onClick={() => setFocusMode((value) => !value)}
          >
            {focusMode ? '◉' : '◌'}
          </button>

          <button
            className="icon-button"
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            onClick={() => setTheme((value) => value === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? '☾' : '☀'}
          </button>

          <button
            className="secondary-button"
            onClick={handleLogout}
            disabled={authBusy}
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="workspace">
        {!focusMode && (
          <aside className="sidebar">
            <div className="sidebar-label">WORKSPACE</div>

            <nav className="navigation" aria-label="Main navigation">
              {navItems.map((item) => (
                <button
                  key={item.label}
                  className={`nav-item ${activePage === item.label ? 'active' : ''}`}
                  onClick={() => navigateTo(item.label)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.label}</span>
                  {activePage === item.label && <span className="nav-indicator" />}
                </button>
              ))}
            </nav>

            <div className="sidebar-bottom">
              <div className="privacy-card">
                <span className="privacy-icon">◇</span>
                <div>
                  <strong>Privacy first</strong>
                  <p>Window titles are not displayed here.</p>
                </div>
              </div>
              <div className="sidebar-version">ATTENTION PLATFORM · 0.1</div>
            </div>
          </aside>
        )}

        <section className="main-content">
          {focusMode ? (
            <section className="immersive-view" data-focus-theme={focusScene}>
              <div className="ambient-orb orb-one" />
              <div className="ambient-orb orb-two" />

              <div className="immersive-content">
                <span className="eyebrow">YOUR QUIET SPACE</span>

                <div className="scene-switcher" role="group" aria-label="Choose focus environment">
                  {focusScenes.map((scene) => (
                    <button
                      key={scene.id}
                      type="button"
                      className={`scene-option ${focusScene === scene.id ? 'active' : ''}`}
                      aria-pressed={focusScene === scene.id}
                      onClick={() => setFocusScene(scene.id)}
                    >
                      {scene.label}
                    </button>
                  ))}
                </div>

                <div className="zen-symbol" aria-hidden="true">
                  {focusScene === 'zen' ? '☯' : focusScene === 'nature' ? '❋' : '☾'}
                </div>

                <h1>
                  {focusScene === 'zen'
                    ? 'Return to the present.'
                    : focusScene === 'nature'
                      ? 'Reconnect with nature.'
                      : 'Find your quiet night.'}
                </h1>

                <p className="immersive-description">
                  {focusScene === 'zen'
                    ? 'One task. One breath. One moment at a time.'
                    : focusScene === 'nature'
                      ? 'Breathe slowly. Let your thoughts settle.'
                      : 'Slow down. Breathe deeply. Focus gently.'}
                </p>

                <div className="focus-clock" role="timer" aria-label={`Time remaining ${formatTime(remaining)}`}>
                  {formatTime(remaining)}
                </div>

                <p className="clock-caption" aria-live="polite">
                  {running
                    ? 'Deep work in progress'
                    : sessionActive
                      ? 'Session paused'
                      : 'Ready when you are'}
                </p>

                {sessionError && <p role="alert" className="session-error">{sessionError}</p>}

                {!sessionActive && (
                  <div className="duration-picker" aria-label="Choose focus duration">
                    {durations.map((value) => (
                      <button
                        key={value}
                        type="button"
                        className={duration === value ? 'duration-chip selected' : 'duration-chip'}
                        aria-pressed={duration === value}
                        onClick={() => changeDuration(value)}
                      >
                        {value} min
                      </button>
                    ))}
                  </div>
                )}

                <div className="focus-actions">
                  <button
                    className="primary-button"
                    disabled={sessionBusy}
                    onClick={sessionActive ? togglePause : startSession}
                  >
                    {sessionBusy
                      ? 'Please wait...'
                      : running
                        ? 'Ⅱ Pause session'
                        : sessionActive
                          ? '▶ Resume session'
                          : '▶ Begin focusing'}
                  </button>

                  {sessionActive && (
                    <button className="secondary-button" disabled={sessionBusy} onClick={stopSession}>
                      Stop
                    </button>
                  )}
                </div>

                <button className="exit-focus" onClick={() => setFocusMode(false)}>
                  Return to dashboard
                </button>
              </div>
            </section>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR PERSONAL WORKSPACE</div>
                  <h1>
                    {activePage === 'Today'
                      ? `Welcome back, ${user.name || 'there'}`
                      : activePage === 'Focus'
                        ? 'Your focus space'
                        : activePage === 'Stats'
                          ? 'Your attention insights'
                          : activePage}
                  </h1>
                  <p className="page-subtitle">
                    {activePage === 'Today'
                      ? 'Make room for what matters today.'
                      : activePage === 'Stats'
                        ? 'Understand your patterns and make time for what matters.'
                        : `Explore your ${activePage.toLowerCase()} workspace.`}
                  </p>
                </div>
                <div className="date-pill">◷ {getTodayDate()}</div>
              </div>

              {dataError && <p role="alert" className="session-error">{dataError}</p>}
              {loadingData && <p className="demo-note">Loading your saved data...</p>}

              {activePage === 'Today' && (
                <>
                  <div className="stats-grid">
                    <article className="stat-card">
                      <div className="stat-top">
                        <span>Screen time</span>
                        <span className="stat-icon blue">◷</span>
                      </div>
                      <div className="stat-value">{todayStats ? formatMinutes(screenTime) : '—'}</div>
                      <div className="stat-foot">Today's recorded activity</div>
                    </article>

                    <article className="stat-card">
                      <div className="stat-top">
                        <span>Focus time</span>
                        <span className="stat-icon green">◉</span>
                      </div>
                      <div className="stat-value">{todayStats ? formatMinutes(focusTime) : '—'}</div>
                      <div className="stat-foot"><span>Goal: {formatMinutes(dailyGoal * 60)}</span></div>
                      <div className="goal-progress"><span style={{ width: `${goalPercent}%` }} /></div>
                    </article>

                    <article className="stat-card">
                      <div className="stat-top">
                        <span>Task switches</span>
                        <span className="stat-icon amber">⇄</span>
                      </div>
                      <div className="stat-value">{todayStats ? taskSwitches : '—'}</div>
                      <div className="stat-foot">Today's recorded switches</div>
                    </article>
                  </div>

                  <div className="dashboard-grid">
                    <article className="panel timeline-panel">
                      <div className="panel-heading">
                        <div><h2>Today's timeline</h2><p>Recorded activity throughout the day</p></div>
                        <span className="live-tag"><span className="status-dot" /> Activity</span>
                      </div>

                      <div className="timeline-chart" aria-label="Recorded hourly activity timeline">
                        {Array.from({ length: 24 }, (_, index) => {
                          const item = timeline.find((entry) => entry.hour === index)
                          const activeSeconds = item?.active_sec || 0
                          const idleSeconds = item?.idle_sec || 0
                          const total = activeSeconds + idleSeconds
                          const maxTotal = Math.max(
                            ...timeline.map((entry) => (entry.active_sec || 0) + (entry.idle_sec || 0)),
                            1,
                          )
                          const height = total > 0
                            ? Math.max(5, Math.min(100, (activeSeconds / maxTotal) * 100))
                            : 3

                          return (
                            <div className="timeline-column" key={index}>
                              <span
                                className={`timeline-bar ${total === 0 ? 'idle' : 'focused'}`}
                                title={`${index}:00 · ${formatMinutes(activeSeconds)} active`}
                                style={{ height: `${height}%` }}
                              />
                            </div>
                          )
                        })}
                      </div>

                      <div className="timeline-labels">
                        <span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>Now</span>
                      </div>
                      <div className="chart-legend">
                        <span><i className="legend-focus" /> Active</span>
                        <span><i className="legend-idle" /> Idle / no data</span>
                      </div>
                    </article>

                    <article className="panel apps-panel">
                      <div className="panel-heading">
                        <div><h2>Top applications</h2><p>Where your recorded time goes</p></div>
                        <button className="text-button" onClick={() => navigateTo('Apps')}>View all ↗</button>
                      </div>

                      <div className="app-list">
                        {topApps.length ? topApps.slice(0, 4).map((app, index) => {
                          const maxTime = Math.max(...topApps.map((item) => item.total_sec || 0), 1)
                          return (
                            <div className="app-row" key={app.app_name}>
                              <div className="app-icon">{['</>', '◎', '◉', '>_'][index % 4]}</div>
                              <div className="app-details">
                                <div className="app-name-row">
                                  <strong>{app.app_name}</strong>
                                  <span>{formatMinutes(app.total_sec)}</span>
                                </div>
                                <div className="app-progress">
                                  <span style={{ width: `${(app.total_sec / maxTime) * 100}%` }} />
                                </div>
                              </div>
                            </div>
                          )
                        }) : <p className="demo-note">No application activity recorded yet. Check that the desktop agent is running and syncing.</p>}
                      </div>
                    </article>
                  </div>

                  <article className="focus-cta">
                    <div className="cta-symbol">◉</div>
                    <div className="cta-copy">
                      <strong>Ready to do your best work?</strong>
                      <p>Put distractions aside and give one thing your attention.</p>
                    </div>
                    <button className="primary-button" onClick={startSession} disabled={sessionBusy}>
                      ▶ Start focus session
                    </button>
                  </article>

                  {recentActivity.length > 0 && (
                    <article className="panel">
                      <div className="panel-heading">
                        <div><h2>Recent activity</h2><p>Latest synced activity records</p></div>
                      </div>
                      <div className="app-list">
                        {recentActivity.slice(0, 5).map((activity, index) => (
                          <div className="app-row" key={activity.id || index}>
                            <div className="app-icon">◷</div>
                            <div className="app-details">
                              <div className="app-name-row">
                                <strong>{activity.app_name || 'Application activity'}</strong>
                                <span>{formatMinutes(activity.duration_sec || activity.active_sec || 0)}</span>
                              </div>
                              <p>{activity.started_at ? new Date(activity.started_at).toLocaleString() : 'Recorded activity'}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </article>
                  )}

                  <div className="demo-note">
                    Statistics and application usage shown here come from the backend. Desktop activity requires the agent to be running and authenticated.
                  </div>
                </>
              )}

              {activePage === 'Focus' && (
                <article className="panel standalone-focus">
                  <span className="eyebrow">FOCUS SESSION</span>
                  <h2>Give one thing your attention.</h2>
                  <p>Choose a duration and enter your focus session.</p>

                  {!sessionActive && (
                    <div className="duration-picker">
                      {durations.map((value) => (
                        <button
                          key={value}
                          className={duration === value ? 'duration-chip selected' : 'duration-chip'}
                          onClick={() => changeDuration(value)}
                        >
                          {value} min
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="standalone-timer">{formatTime(remaining)}</div>
                  {sessionError && <p role="alert" className="session-error">{sessionError}</p>}

                  <div className="focus-actions">
                    <button className="primary-button" disabled={sessionBusy} onClick={sessionActive ? togglePause : startSession}>
                      {sessionBusy ? 'Please wait...' : running ? 'Ⅱ Pause' : sessionActive ? '▶ Resume' : '▶ Start session'}
                    </button>
                    {sessionActive && <button className="secondary-button" disabled={sessionBusy} onClick={stopSession}>Stop</button>}
                    <button className="secondary-button" onClick={() => setFocusMode(true)}>Enter immersive mode</button>
                  </div>

                  <p className="demo-note">Sessions started this visit: {sessionCount}.</p>

                  {focusHistory.length > 0 && (
                    <div className="app-list">
                      <h3>Recent focus sessions</h3>
                      {focusHistory.map((item) => (
                        <div className="app-row" key={item.id}>
                          <div className="app-icon">◉</div>
                          <div className="app-details">
                            <div className="app-name-row">
                              <strong>{item.label || 'Focus session'}</strong>
                              <span>{item.planned_min} min</span>
                            </div>
                            <p>
                              {new Date(item.started_at).toLocaleString()} · {item.status} · {item.switch_count} switch(es)
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              )}

              {activePage === 'Apps' && (
                <article className="panel table-panel">
                  <div className="panel-heading">
                    <div><h2>Application usage</h2><p>Applications reported by the activity tracker</p></div>
                  </div>

                  <div className="usage-table">
                    <div className="usage-row usage-header">
                      <span>Application</span><span>Category</span><span>Total time</span><span>Usage</span>
                    </div>

                    {topApps.length ? topApps.map((app, index) => {
                      const maxTime = Math.max(...topApps.map((item) => item.total_sec || 0), 1)
                      return (
                        <div className="usage-row" key={app.app_name}>
                          <strong>{['</>', '◎', '◉', '>_'][index % 4]} &nbsp; {app.app_name}</strong>
                          <span>Tracked application</span>
                          <span>{formatMinutes(app.total_sec)}</span>
                          <span className="table-progress"><i style={{ width: `${(app.total_sec / maxTime) * 100}%` }} /></span>
                        </div>
                      )
                    }) : <p className="demo-note">No application usage is available yet.</p>}
                  </div>
                </article>
              )}

              {activePage === 'Stats' && (
                <>
                  <div className="stats-grid">
                    <article className="stat-card">
                      <div className="stat-top"><span>Total screen time</span><span className="stat-icon blue">◷</span></div>
                      <div className="stat-value">{todayStats ? formatMinutes(screenTime) : '—'}</div>
                      <div className="stat-foot">Today · Backend data</div>
                    </article>
                    <article className="stat-card">
                      <div className="stat-top"><span>Focused time</span><span className="stat-icon green">◉</span></div>
                      <div className="stat-value">{todayStats ? formatMinutes(focusTime) : '—'}</div>
                      <div className="stat-foot">Daily focus time</div>
                    </article>
                    <article className="stat-card">
                      <div className="stat-top"><span>Task switches</span><span className="stat-icon amber">⇄</span></div>
                      <div className="stat-value">{todayStats ? taskSwitches : '—'}</div>
                      <div className="stat-foot">Recorded today</div>
                    </article>
                  </div>

                  <div className="dashboard-grid">
                    <article className="panel timeline-panel">
                      <div className="panel-heading">
                        <div><h2>Hourly activity</h2><p>Activity recorded today</p></div>
                        <span className="live-tag">Today</span>
                      </div>

                      <div className="timeline-chart">
                        {Array.from({ length: 24 }, (_, index) => {
                          const item = timeline.find((entry) => entry.hour === index)
                          const activeSeconds = item?.active_sec || 0
                          const maxSeconds = Math.max(...timeline.map((entry) => entry.active_sec || 0), 1)
                          const height = activeSeconds ? Math.max(5, (activeSeconds / maxSeconds) * 100) : 3

                          return (
                            <div className="timeline-column" key={index}>
                              <span
                                className={`timeline-bar ${activeSeconds ? 'focused' : 'idle'}`}
                                style={{ height: `${height}%` }}
                                title={`${index}:00 · ${formatMinutes(activeSeconds)}`}
                              />
                            </div>
                          )
                        })}
                      </div>

                      <div className="timeline-labels">
                        <span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>Now</span>
                      </div>
                      <div className="chart-legend">
                        <span><i className="legend-focus" /> Active</span>
                        <span><i className="legend-idle" /> No activity</span>
                      </div>
                    </article>

                    <article className="panel apps-panel">
                      <div className="panel-heading">
                        <div><h2>Time by application</h2><p>Recorded application usage</p></div>
                        <button className="text-button" onClick={() => navigateTo('Apps')}>View all ↗</button>
                      </div>

                      <div className="app-list">
                        {topApps.slice(0, 4).map((app) => (
                          <div className="app-row" key={app.app_name}>
                            <div className="app-icon">◷</div>
                            <div className="app-details">
                              <div className="app-name-row">
                                <strong>{app.app_name}</strong>
                                <span>{formatMinutes(app.total_sec)}</span>
                              </div>
                              <div className="app-progress">
                                <span style={{ width: `${Math.min(100, (app.total_sec / Math.max(...topApps.map((item) => item.total_sec || 0), 1)) * 100)}%` }} />
                              </div>
                            </div>
                          </div>
                        ))}
                        {!topApps.length && <p className="demo-note">No recorded app usage yet.</p>}
                      </div>
                    </article>
                  </div>

                  <article className="panel timeline-panel">
                    <div className="panel-heading">
                      <div><h2>Daily history</h2><p>Active time per day</p></div>
                      <div className="duration-picker">
                        {[7, 30].map((value) => (
                          <button
                            key={value}
                            type="button"
                            className={rangeDays === value ? 'duration-chip selected' : 'duration-chip'}
                            aria-pressed={rangeDays === value}
                            onClick={() => setRangeDays(value)}
                          >
                            {value} days
                          </button>
                        ))}
                      </div>
                    </div>

                    {rangeError && <p role="alert" className="session-error">{rangeError}</p>}

                    <div className="timeline-chart" aria-label="Daily active time">
                      {(rangeStats?.daily || []).map((day) => {
                        const maxDay = Math.max(
                          ...(rangeStats?.daily || []).map((entry) => entry.active_sec || 0),
                          1,
                        )
                        const height = day.active_sec
                          ? Math.max(5, (day.active_sec / maxDay) * 100)
                          : 3

                        return (
                          <div className="timeline-column" key={day.day}>
                            <span
                              className={`timeline-bar ${day.active_sec ? 'focused' : 'idle'}`}
                              style={{ height: `${height}%` }}
                              title={`${day.day} · ${formatMinutes(day.active_sec)}`}
                            />
                          </div>
                        )
                      })}
                    </div>

                    {rangeStats?.daily?.length > 0 && (
                      <div className="timeline-labels">
                        <span>{rangeStats.daily[0].day}</span>
                        <span>{rangeStats.daily[rangeStats.daily.length - 1].day}</span>
                      </div>
                    )}

                    {rangeStats ? (
                      <p className="demo-note">
                        Last {rangeDays} days: screen time {formatMinutes(rangeStats.screen_time_sec)} ·
                        focus {formatMinutes(rangeStats.focus_sec)} ·
                        {' '}{rangeStats.task_switches} task switches
                      </p>
                    ) : (
                      !rangeError && <p className="demo-note">Loading history...</p>
                    )}
                  </article>
                </>
              )}

              {activePage === 'Goals' && (
                <div className="dashboard-grid">
                  <article className="panel">
                    <div className="panel-heading">
                      <div><h2>Your focus goals</h2><p>Create and manage goals saved by the backend</p></div>
                    </div>

                    <form onSubmit={handleCreateGoal}>
                      <label>
                        Goal type
                        <select value={newGoalType} onChange={(event) => setNewGoalType(event.target.value)}>
                          <option value="daily_focus_min">Daily focus minutes</option>
                          <option value="max_task_switches">Maximum task switches</option>
                          <option value="max_app_min">Maximum app minutes</option>
                        </select>
                      </label>

                      <label>
                        Target value
                        <input type="number" min="1" value={newGoalTarget} onChange={(event) => setNewGoalTarget(event.target.value)} required />
                      </label>

                      {newGoalType === 'max_app_min' && (
                        <label>
                          Application name
                          <input value={newGoalApp} onChange={(event) => setNewGoalApp(event.target.value)} required maxLength={255} />
                        </label>
                      )}

                      {goalError && <p role="alert" className="session-error">{goalError}</p>}
                      <button className="primary-button" type="submit">Add goal</button>
                    </form>
                  </article>

                  <article className="panel">
                    <div className="panel-heading"><div><h2>Saved goals</h2><p>{goals.length} goal(s)</p></div></div>
                    <div className="app-list">
                      {goals.map((goal) => (
                        <div className="app-row" key={goal.id}>
                          <div className="app-icon">⚑</div>
                          <div className="app-details">
                            <div className="app-name-row">
                              <strong>{goal.type.replaceAll('_', ' ')}</strong>
                              <span>{goal.target_value}</span>
                            </div>
                            <p>{goal.app_name || 'Daily target'} · {goal.is_active ? 'Active' : 'Inactive'}</p>
                            <button className="secondary-button" onClick={() => handleDeleteGoal(goal)}>Delete</button>
                            <button className="secondary-button" onClick={() => handleToggleGoal(goal)}>
                              {goal.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                          </div>
                        </div>
                      ))}
                      {!goals.length && <p className="demo-note">No goals yet. Create your first goal.</p>}
                    </div>
                  </article>
                </div>
              )}

              {activePage === 'Settings' && (
                <article className="panel placeholder-panel">
                  <span className="placeholder-icon">⚙</span>
                  <h2>Your workspace, your rules</h2>
                  <p>These preferences are saved to your account.</p>

                  <form onSubmit={handleSaveProfile}>
                    <label>
                      Your name
                      <input
                        value={profileName}
                        onChange={(event) => setProfileName(event.target.value)}
                        maxLength={100}
                        required
                      />
                    </label>
                    {profileMessage && <p role="status">{profileMessage}</p>}
                    <button className="secondary-button" type="submit">Update name</button>
                  </form>

                  {settings ? (
                    <form onSubmit={handleSaveSettings}>
                      <label>
                        Appearance
                        <select value={theme} onChange={(event) => setTheme(event.target.value)}>
                          <option value="light">Light</option>
                          <option value="dark">Dark</option>
                        </select>
                      </label>

                      <label>
                        Daily focus goal (minutes)
                        <input
                          type="number"
                          min="15"
                          max="720"
                          value={settings.daily_focus_goal_min}
                          onChange={(event) => setSettings({ ...settings, daily_focus_goal_min: Number(event.target.value) })}
                          required
                        />
                      </label>

                      <label>
                        Idle threshold (seconds)
                        <input
                          type="number"
                          min="30"
                          max="900"
                          value={settings.idle_threshold_sec}
                          onChange={(event) => setSettings({ ...settings, idle_threshold_sec: Number(event.target.value) })}
                          required
                        />
                      </label>

                      <label>
                        <input
                          type="checkbox"
                          checked={settings.store_window_titles}
                          onChange={(event) => setSettings({ ...settings, store_window_titles: event.target.checked })}
                        />
                        Allow storing window titles
                      </label>

                      <label>
                        Ignored applications (comma-separated)
                        <input
                          value={(settings.ignored_apps || []).join(', ')}
                          onChange={(event) => setSettings({
                            ...settings,
                            ignored_apps: event.target.value.split(',').map((app) => app.trim()).filter(Boolean),
                          })}
                        />
                      </label>

                      <label>
                        Timezone (e.g. Asia/Kolkata)
                        <input
                          value={settings.timezone}
                          onChange={(event) => setSettings({ ...settings, timezone: event.target.value })}
                          maxLength={64}
                        />
                      </label>

                      {settingsMessage && <p role="status">{settingsMessage}</p>}
                      <button className="primary-button" type="submit">Save settings</button>
                    </form>
                  ) : (
                    <p className="demo-note">Settings could not be loaded. Refresh after confirming that the backend is running.</p>
                  )}
                </article>
              )}

              {activePage === 'Settings' && (
                <article className="panel placeholder-panel">
                  <h2>Delete my data</h2>
                  <p>
                    This permanently removes your recorded activity and related data from the
                    server. It cannot be undone. Your account stays.
                  </p>

                  <form onSubmit={handleDeleteData}>
                    <label>
                      Type DELETE to confirm
                      <input
                        value={deleteConfirm}
                        onChange={(event) => setDeleteConfirm(event.target.value)}
                        autoComplete="off"
                      />
                    </label>
                    {deleteMessage && <p role="status">{deleteMessage}</p>}
                    <button
                      className="secondary-button"
                      type="submit"
                      disabled={deleteConfirm !== 'DELETE'}
                    >
                      Delete my data
                    </button>
                  </form>
                </article>
              )}

              <footer className="page-footer">
                <span>Designed for deeper work.</span>
                <span>Privacy matters · Attention Platform</span>
              </footer>
            </>
          )}
        </section>
      </div>
    </main>
  )
}

export default App
