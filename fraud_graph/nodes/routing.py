from ..state import FraudState
LEGITIMATE_SCORE_THRESHOLD = 0.15

def route_on_score(state: FraudState) -> str:
    return 'decision_ok'

def decision_ok(state: FraudState) -> FraudState:
    risk_score = state.get('risk_score', 0.0)
    if risk_score < LEGITIMATE_SCORE_THRESHOLD:
        decision = 'LEGITIMATE'
        explanation = f'Score de risque très faible ({risk_score:.2f}): transaction légitime'
    else:
        decision = 'SUSPECT'
        explanation = f'Score de risque ({risk_score:.2f}): élément suspect détecté (à trier)'
    return {**state, 'decision': decision, 'llm_result': None, 'explanation': explanation}