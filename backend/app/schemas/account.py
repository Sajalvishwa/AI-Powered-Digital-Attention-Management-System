from pydantic import BaseModel


class DeleteDataOut(BaseModel):
    deleted: dict[str, int]  # table name -> number of rows removed
