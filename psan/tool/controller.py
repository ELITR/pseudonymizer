from typing import Dict, List, Optional, Tuple


from psan.tool.model import (AnnotationDecision, AnnotationSource, Confidence,
                             Evidence, EvidenceType, Interval, Rule, RuleType,
                             Word)


class Controller:
    def __init__(self, cursor, document_id: int, user_id: int = None) -> None:
        self._cursor = cursor
        self._document_id = document_id
        self._user_id = user_id

    def set_rule(self, rule_type: Rule, condition: List[str], confidence: int) -> Rule:
        """Adds new rule into db or update existing and returns it's ID"""
        self._cursor.execute("INSERT INTO rule (type, condition, confidence, author) VALUES (%s, %s, %s, %s) "
                             " ON CONFLICT (type, condition) DO UPDATE"
                             " SET confidence=EXCLUDED.confidence, author=EXCLUDED.author RETURNING id",
                             (rule_type.value, condition, confidence, self._user_id))
        return Rule(self._cursor.fetchone()["id"])

    def add_candidate_rule(self, tokens: List[str], token_annotation_id: int) -> Optional[Rule]:
        """Adds new candidate rule and returns it's ID or retrun None"""
        self._cursor.execute("INSERT INTO rule (type, condition, confidence, author, source) VALUES (%s, %s, %s, %s, %s) "
                             " ON CONFLICT (type, condition) DO NOTHING"
                             " RETURNING id",
                             (RuleType.WORD_TYPE.value, tokens, Confidence.CANDIDATE, self._user_id, token_annotation_id))
        data = self._cursor.fetchone()
        if data:
            rule = Rule(data["id"])
            self.connect(token_annotation_id, rule)
            return rule
        else:
            return None

    def drop_candidate_rule(self, token_annotation_id: int) -> None:
        """Drops candidates rule connected to annotation"""
        self._cursor.execute("DELETE FROM rule WHERE type = %s and source = %s and confidence >= %s",
                             (RuleType.WORD_TYPE.value, token_annotation_id, Confidence.CANDIDATE))

    def add_ne_type(self, ne_type: str) -> Rule:
        """Adds new NE type into db and returns it's ID (or return duplicate rule ID)"""
        self._cursor.execute("INSERT INTO rule (type, condition, confidence, author) VALUES (%s, %s, %s, %s) "
                             " ON CONFLICT (type, condition) DO UPDATE"
                             " SET confidence=EXCLUDED.confidence, author=EXCLUDED.author RETURNING id",
                             (RuleType.NE_TYPE.value, [ne_type], Confidence.CANDIDATE, self._user_id))
        return Rule(self._cursor.fetchone()["id"])

    def token_annotation(self, interval: Interval, decision: AnnotationDecision) -> int:
        """ Annotate text interval using token level decision"""
        user_annotation = AnnotationSource.USER.value
        # Delete nested USER annotations
        self._cursor.execute("DELETE FROM annotation"
                             " WHERE submission = %s and source = %s"
                             " and %s <= ref_start and ref_end <= %s and (ref_end - ref_start) < %s",
                             (self._document_id, user_annotation, interval.start, interval.end, interval.end - interval.start))
        # Insert or update annotation
        self._cursor.execute("INSERT INTO annotation (submission, ref_start, ref_end, token_level, source, author)"
                             " VALUES (%s, %s, %s, %s, %s, %s)"
                             " ON CONFLICT (submission, ref_start, ref_end) DO UPDATE"
                             " SET token_level=EXCLUDED.token_level, author=EXCLUDED.author"
                             " RETURNING id",
                             (self._document_id, interval.start, interval.end, decision.value, user_annotation, self._user_id))
        return self._cursor.fetchone()["id"]

    def annotate_from_rule(self, interval: Interval,
                           rule: Rule,
                           token_level_decision: Optional[AnnotationDecision] = None) -> None:
        """ Annotate text interval with rule """
        token_decision_str = token_level_decision.value if token_level_decision else None
        self._cursor.execute("SELECT id FROM annotation WHERE submission = %s and ref_start = %s and ref_end = %s",
                             (self._document_id, interval.start, interval.end))
        data = self._cursor.fetchone()
        if not data:
            self._cursor.execute("INSERT INTO annotation (submission, ref_start, ref_end, token_level, author)"
                                 " VALUES (%s, %s, %s, %s, %s)"
                                 " RETURNING id",
                                 (self._document_id, interval.start, interval.end, token_decision_str, self._user_id))
            data = self._cursor.fetchone()
        annotation_id = data["id"]
        self.connect(annotation_id, rule)

    def connect(self, annotation_id, rule: Rule) -> None:
        """ Adds connection from annotation to rule """
        self._cursor.execute("INSERT INTO annotation_rule (annotation, rule) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                             (annotation_id, rule.id))

    def set_label(self, interval: Interval, label_id: int) -> None:
        """ Sets label for selected interval """
        self._cursor.execute("UPDATE annotation SET label = %s, author = %s"
                             " WHERE submission = %s and ref_start = %s and ref_end = %s",
                             (label_id, self._user_id, self._document_id, interval.start, interval.end))

    def set_rule_label(self, types: List[str], label_id: int) -> None:
        """ Sets label for type rule """
        self._cursor.execute("UPDATE rule SET label = %s, author = %s"
                             " WHERE type = %s and condition = %s",
                             (label_id, self._user_id, RuleType.WORD_TYPE.value, types))

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

    def get_decisions(self, interval: Optional[Interval], min_confidence, with_replacement=False) -> List[Dict[str, str]]:
        """Return list of annotation decisions and labels withing selected interval"""
        decisions = []
        # Query - where part
        if interval:
            where_cls = " WHERE submission = %s and %s<=ref_start and ref_start<=%s"
            where_args = (self._document_id, interval.start, interval.end)
        else:
            where_cls = " WHERE submission = %s"
            where_args = (self._document_id,)
        self._cursor.execute("SELECT ref_start, ref_end, token_level, rule_level, l.name as label, l.replacement as replacement"
                             " FROM annotation a"
                             " LEFT JOIN annotation_rule ar ON ar.annotation = a.id"
                             " LEFT JOIN rule r ON r.id = ar.rule AND r.label IS NOT NULL AND r.confidence < 0"
                             " LEFT JOIN label l ON COALESCE(a.label, r.label) = l.id"
                             + where_cls +  # nosec
                             " ORDER BY ref_start",
                             where_args)
        # Prepare decisions
        for row in self._cursor:
            # Decision sum-up
            if row["token_level"]:
                # Token level decision
                decision = row["token_level"]
            else:
                # Rule level decision
                rule_level = row["rule_level"]
                if rule_level <= -min_confidence:
                    decision = AnnotationDecision.SECRET.value
                elif min_confidence <= rule_level:
                    decision = AnnotationDecision.PUBLIC.value
                else:
                    decision = None
            # Decision row
            decision = {"start": row["ref_start"], "end": row["ref_end"], "decision": decision, "label": row["label"]}
            if with_replacement:
                decision["replacement"] = row["replacement"]
            decisions.append(decision)

        return decisions
