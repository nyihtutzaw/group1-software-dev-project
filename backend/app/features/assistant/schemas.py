from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

# One answer is capped at MAX_ANSWER_TOKENS (service.py), well under this many characters.
MAX_MESSAGE_CHARS = 12_000
MAX_MESSAGES = 40


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatIn(BaseModel):
    """The conversation so far, oldest first, ending with the new question.

    The server keeps no history: the browser sends it with every question.
    """

    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def ends_with_a_question(self) -> Self:
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be the user's question")
        return self


class AssistantStatusOut(BaseModel):
    enabled: bool
    model: str
    documents: list[str]
