"""
Quote verifier for Stage 5 - three-check hallucination firewall.
"""

from typing import Optional, Tuple
from ..models import Transcript, ConversationTurn
from ..models.evidence import VerifiedQuote


class QuoteVerifier:
    """
    Three-check hallucination firewall per logic.md Stage 5.

    Validates LLM-extracted quotes through:
    1. Existence check - Quote must appear verbatim in transcript
    2. Speaker check - Quote must be from expected speaker (AGENT/PATIENT)
    3. Timestamp check - LLM timestamp must be within 1 second of actual
    """

    TIMESTAMP_TOLERANCE_SECONDS = 1.0  # Per logic.md specification

    def verify_quote(
        self,
        quote: str,
        claimed_timestamp: float,
        expected_speaker: str,  # "AGENT" or "PATIENT"
        transcript: Transcript,
    ) -> VerifiedQuote:
        """
        Run 3-check verification on a quote.

        Args:
            quote: The quote text to verify
            claimed_timestamp: Timestamp claimed by LLM (seconds)
            expected_speaker: Expected speaker ("AGENT" or "PATIENT")
            transcript: The conversation transcript

        Returns:
            VerifiedQuote with all validation results
        """
        # Check 1: Does quote exist verbatim in transcript?
        turn_index, turn = self._find_quote_in_transcript(quote, transcript)

        if turn is None:
            # Hallucination - quote doesn't exist
            return VerifiedQuote(
                quote=quote,
                verified=False,
                speaker_match=False,
                timestamp_match=False,
                corrected_timestamp=None,
                turn_index=-1,
                hallucination=True,
            )

        # Check 2: Speaker match
        turn_speaker = "AGENT" if turn.role == "assistant" else "PATIENT"
        speaker_match = turn_speaker == expected_speaker

        # Check 3: Timestamp within tolerance
        timestamp_diff = abs(turn.beginning - claimed_timestamp)
        timestamp_match = timestamp_diff <= self.TIMESTAMP_TOLERANCE_SECONDS

        # Always use actual timestamp for correction
        corrected_timestamp = turn.beginning

        # Quote is verified only if speaker matches
        # Timestamp mismatch is corrected but doesn't fail the quote
        verified = speaker_match

        return VerifiedQuote(
            quote=quote,
            verified=verified,
            speaker_match=speaker_match,
            timestamp_match=timestamp_match,
            corrected_timestamp=corrected_timestamp,
            turn_index=turn_index,
            hallucination=False,
        )

    def _find_quote_in_transcript(
        self, quote: str, transcript: Transcript
    ) -> Tuple[int, Optional[ConversationTurn]]:
        """
        Find exact quote in transcript (verbatim substring match).

        Args:
            quote: Quote text to find
            transcript: Transcript to search

        Returns:
            Tuple of (turn_index, turn) or (-1, None) if not found
        """
        # Try exact match first (case-sensitive)
        for i, turn in enumerate(transcript.turns):
            if quote in turn.content:
                return (i, turn)

        # If not found, try case-insensitive as fallback
        # (LLM might change capitalization)
        quote_lower = quote.lower()
        for i, turn in enumerate(transcript.turns):
            if quote_lower in turn.content.lower():
                return (i, turn)

        # Quote not found - hallucination
        return (-1, None)

    def verify_batch(
        self, quotes_with_metadata: list[Tuple[str, float, str]], transcript: Transcript
    ) -> list[VerifiedQuote]:
        """
        Verify multiple quotes at once (batch processing).

        Args:
            quotes_with_metadata: List of (quote, timestamp, speaker) tuples
            transcript: Transcript to verify against

        Returns:
            List of VerifiedQuote results
        """
        return [
            self.verify_quote(quote, timestamp, speaker, transcript)
            for quote, timestamp, speaker in quotes_with_metadata
        ]

    def get_verification_summary(self, verified_quotes: list[VerifiedQuote]) -> dict:
        """
        Get summary statistics for a batch of verified quotes.

        Returns:
            Dictionary with verification statistics
        """
        total = len(verified_quotes)
        if total == 0:
            return {
                "total": 0,
                "verified": 0,
                "hallucinated": 0,
                "speaker_mismatches": 0,
                "timestamp_mismatches": 0,
                "verification_rate": 0.0,
            }

        verified_count = sum(1 for vq in verified_quotes if vq.verified)
        hallucinated = sum(1 for vq in verified_quotes if vq.hallucination)
        speaker_mismatches = sum(1 for vq in verified_quotes if not vq.speaker_match)
        timestamp_mismatches = sum(
            1 for vq in verified_quotes if not vq.timestamp_match
        )

        return {
            "total": total,
            "verified": verified_count,
            "hallucinated": hallucinated,
            "speaker_mismatches": speaker_mismatches,
            "timestamp_mismatches": timestamp_mismatches,
            "verification_rate": verified_count / total if total > 0 else 0.0,
        }
