"""
Transcript models for representing conversation transcripts.
"""

from typing import List
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in a conversation"""

    role: str = Field(..., description="Role of the speaker (user or assistant)")
    content: str = Field(..., description="The spoken text")
    beginning: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")

    @property
    def duration(self) -> float:
        """Calculate duration of this turn"""
        return self.end - self.beginning


class Transcript(BaseModel):
    """Complete conversation transcript"""

    turns: List[ConversationTurn] = Field(
        ..., description="List of conversation turns in chronological order"
    )

    @property
    def total_duration(self) -> float:
        """Total duration of the conversation"""
        if not self.turns:
            return 0.0
        return self.turns[-1].end - self.turns[0].beginning

    def get_assistant_turns(self) -> List[ConversationTurn]:
        """Get only assistant turns (for analysis)"""
        return [turn for turn in self.turns if turn.role == "assistant"]

    def get_user_turns(self) -> List[ConversationTurn]:
        """Get only user turns"""
        return [turn for turn in self.turns if turn.role == "user"]
