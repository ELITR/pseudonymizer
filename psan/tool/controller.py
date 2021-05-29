from typing import List, Optional, Tuple

from psan.tool.model import (AnnotationDecision, Confidence, Evidence, EvidenceType, Interval,
                             Rule, RuleType, Word)


class Controller:
    def __init__(self, cursor, document_id: int, user_id: int = None) -> None:
        self._cursor = cursor
        self._document_id = document_id
        self._user_id = user_id

    def add_rule(self, rule_type: Rule, condition: List, confidence: int) -> Rule:
        """Adds new rule into db or update existing and returns it's ID"""
        self._cursor.execute("INSERT INTO rule (type, condition, confidence, author) VALUES (%s, %s, %s, %s) "
                             " ON CONFLICT (type, condition) DO UPDATE"
                             " SET confidence=EXCLUDED.confidence, author=EXCLUDED.author RETURNING id",

                             (rule_type.value, condition, confidence, self._user_id))
        return Rule(self._cursor.fetchone()["id"])

    def add_ne_type(self, ne_type: str) -> Rule:
        """Adds new NE type into db and returns it's ID (or return duplicate rule ID)"""
        return self.add_rule(RuleType.NE_TYPE.value, [ne_type], Confidence.CANDIDATE)

    def annotate(self, interval: Interval, token_level_decision: AnnotationDecision) -> None:
        """ Annotate text interval with token level decision """
        self._cursor.execute("INSERT INTO annotation (submission, ref_start, ref_end, token_level, author) VALUES (%s, %s, %s, %s, %s)"
                             " ON CONFLICT (submission, ref_start, ref_end) DO UPDATE"
                             " SET token_level=EXCLUDED.token_level, author=EXCLUDED.author",
                             (self._document_id, interval.start, interval.end, token_level_decision.value, self._user_id))

    def annotate_with_rule(self, interval: Interval, rule: Rule, token_level_decision: Optional[AnnotationDecision] = None) -> None:
        """ Annotate text interval with rule """
        token_decision_str = token_level_decision.value if token_level_decision else None
        self._cursor.execute("INSERT INTO annotation (submission, ref_start, ref_end, token_level, author) VALUES (%s, %s, %s, %s, %s)"
                             " ON CONFLICT (submission, ref_start, ref_end) DO UPDATE"
                             " SET token_level=EXCLUDED.token_level, author=EXCLUDED.author"
                             " RETURNING id",
                             (self._document_id, interval.start, interval.end, token_decision_str, self._user_id))
        annotation_id = self._cursor.fetchone()["id"]
        # Add connection from rule to annotation
        self._cursor.execute("INSERT INTO annotation_rule (annotation, rule) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                             (annotation_id, rule.id))

    def find_rule(self, evidence: Evidence) -> Optional[Rule]:
        """Finds rule in DB according to evidence"""
        if evidence.type == EvidenceType.NE_TYPE:
            self._cursor.execute("SELECT id FROM rule WHERE type = %s and condition = %s",
                                 (RuleType.NE_TYPE.value, evidence.value))
            row = self._cursor.fetchone()
            rule = Rule(row["id"]) if row else None
        elif evidence.type == EvidenceType.WORD_TYPE:
            self._cursor.execute("SELECT id, condition FROM rule WHERE type = %s and condition[1] = %s",
                                 (RuleType.WORD_TYPE.value, evidence.value[0]))
            # Find rule where condition match evidence
            rule = None
            for row in self._cursor:
                condition = row["condition"]
                if condition == evidence.value[:len(condition)]:
                    rule = Rule(row["id"])
                    break
        else:
            # Every evidence type should be supported
            raise RuntimeError(f"Unknown evidence type {evidence.type} for evidence {evidence}")

        # Returns rule or None
        return rule

    def rule_lookup(self, word: Word) -> Tuple[EvidenceType, int]:
        """ Decides how many words following `word` should be captured for next evidence."""
        self._cursor.execute("SELECT condition[1] AS first_word, max(array_length(condition, 1)) as length FROM rule"
                             " WHERE condition[1] = %s GROUP BY first_word", (word.token,))
        row = self._cursor.fetchone()
        if row:
            return EvidenceType.WORD_TYPE, row["length"] - 1
        else:
            return EvidenceType.NONE, 0
