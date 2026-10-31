from app.core.intent_classifier import IntentClassifier, MessageIntent


def test_request_style_prompt_is_question_intent() -> None:
    result = IntentClassifier.classify("Tell me about Datacube AU")

    assert result.intent == MessageIntent.QUESTION


def test_identity_prompt_still_preempts_question_intent() -> None:
    result = IntentClassifier.classify("What projects does Fabian have?")

    assert result.intent == MessageIntent.IDENTITY_QUESTION
