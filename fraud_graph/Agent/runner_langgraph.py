"""Runner pour l'agent LangGraph - compatible avec l'interface existante."""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .agent_langgraph import create_fraud_agent

logger = logging.getLogger(__name__)


class SimpleSession:
    """Session simple compatible avec l'interface Google ADK."""
    
    def __init__(self, session_id: str, app_name: str, user_id: str):
        self.id = session_id
        self.app_name = app_name
        self.user_id = user_id


class SimpleSessionService:
    """Service de session simple compatible avec l'interface Google ADK."""
    
    def create_session(self, app_name: str, user_id: str) -> SimpleSession:
        """Crée une nouvelle session."""
        session_id = str(uuid.uuid4())
        return SimpleSession(session_id, app_name, user_id)


class LangGraphRunner:
    """Runner pour l'agent LangGraph, compatible avec l'interface existante."""
    
    def __init__(self, agent=None):
        """Initialise le runner avec un agent LangGraph."""
        if agent is None:
            agent = create_fraud_agent()
        self.agent = agent
        self.session_service = SimpleSessionService()
    
    async def run_async(
        self,
        user_id: str,
        session_id: str,
        new_message: Any,
    ):
        """Exécute l'agent de manière asynchrone.
        
        Compatible avec l'interface existante pour faciliter la migration.
        
        Args:
            user_id: ID de l'utilisateur (non utilisé mais conservé pour compatibilité)
            session_id: ID de session (utilisé comme thread_id)
            new_message: Message utilisateur (Content ou dict)
        
        Yields:
            Événements de l'exécution de l'agent
        """
        # Extraire le texte du message
        if hasattr(new_message, 'parts'):
            # Format Content avec parts
            text_parts = []
            for part in new_message.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
            message_text = '\n'.join(text_parts)
        elif isinstance(new_message, dict):
            message_text = new_message.get('text', str(new_message))
        elif isinstance(new_message, str):
            message_text = new_message
        else:
            message_text = str(new_message)
        
        # Configuration avec thread_id basé sur session_id
        config = {
            'configurable': {
                'thread_id': session_id
            }
        }
        
        # Simuler les événements de l'agent
        try:
            # Événement de démarrage
            yield type('Event', (), {
                '__class__': type('ToolCall', (), {}),
                'type': 'start',
                'message': 'Starting agent execution'
            })()
            
            # Exécuter l'agent
            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
            
            async for event in self.agent.astream(
                {"messages": [HumanMessage(content=message_text)]},
                config=config
            ):
                # Convertir les événements LangGraph en format compatible
                for node_name, node_output in event.items():
                    logger.debug(f"📦 Node: {node_name}, Output type: {type(node_output)}, Output keys: {list(node_output.keys()) if isinstance(node_output, dict) else 'N/A'}")
                    
                    # Le node "tools" contient les résultats des outils
                    if node_name == "tools" and node_output:
                        logger.debug(f"🔧 Node 'tools' détecté - résultats des outils")
                    
                    if node_output and 'messages' in node_output:
                        for msg in node_output['messages']:
                            logger.debug(f"📨 Message type: {type(msg).__name__}, has tool_calls: {hasattr(msg, 'tool_calls')}")
                            
                            # Détecter les tool calls (AIMessage avec tool_calls)
                            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                                logger.info(f"🔧 AIMessage avec {len(msg.tool_calls)} tool calls détectés")
                                for tool_call in msg.tool_calls:
                                    # Extraire les arguments du tool call
                                    tool_args = {}
                                    if hasattr(tool_call, 'args'):
                                        tool_args = tool_call.args
                                    elif isinstance(tool_call, dict):
                                        tool_args = tool_call.get('args', {})
                                    
                                    # Extraire le nom de l'outil
                                    tool_name = None
                                    if hasattr(tool_call, 'name'):
                                        tool_name = tool_call.name
                                    elif isinstance(tool_call, dict):
                                        tool_name = tool_call.get('name', 'unknown')
                                    elif hasattr(tool_call, 'get'):
                                        tool_name = tool_call.get('name', 'unknown')
                                    
                                    if tool_name:
                                        logger.debug(f"🔧 Tool call détecté: {tool_name} avec args: {tool_args}")
                                        yield type('Event', (), {
                                            '__class__': type('ToolCall', (), {}),
                                            'type': 'tool_call',
                                            'function_name': tool_name,
                                            'function': tool_name,
                                            'name': tool_name,
                                            'args': tool_args,
                                            'arguments': tool_args,
                                        })()
                            
                            # Extraire le contenu textuel des messages
                            content = None
                            if hasattr(msg, 'content'):
                                content = msg.content
                            elif isinstance(msg, dict):
                                content = msg.get('content', '')
                            else:
                                content = str(msg)
                            
                            # Ignorer les ToolMessage (résultats d'outils)
                            if isinstance(msg, ToolMessage):
                                continue
                            
                            # Événement de réponse seulement si contenu textuel
                            if content and content.strip():
                                yield type('Event', (), {
                                    '__class__': type('Content', (), {}),
                                    'content': type('Content', (), {
                                        'parts': [type('Part', (), {'text': str(content)})()],
                                        'text': str(content)
                                    })(),
                                    'text': str(content),
                                    'type': 'response'
                                })()
            
            # Événement de fin
            yield type('Event', (), {
                '__class__': type('End', (), {}),
                'type': 'end',
                'message': 'Agent execution completed'
            })()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'agent: {e}", exc_info=True)
            yield type('Event', (), {
                '__class__': type('Error', (), {}),
                'type': 'error',
                'error': str(e),
                'message': f'Error: {str(e)}'
            })()


def analyze_batch_with_langgraph_agent(
    agent,
    transaction_ids: List[str],
    batch_num: int,
    user_id: str = 'fraud_analyst'
) -> Dict[str, Any]:
    """Analyse un batch de transactions avec l'agent LangGraph.
    
    Compatible avec l'interface analyze_batch_with_agent_sync.
    
    Args:
        agent: L'agent LangGraph
        transaction_ids: Liste des IDs de transactions
        batch_num: Numéro du batch
        user_id: ID de l'utilisateur
    
    Returns:
        Résultat de l'analyse
    """
    batch_start_time = datetime.now()
    session_id = str(uuid.uuid4())
    
    transaction_ids_json = json.dumps(transaction_ids)
    
    user_prompt = f"""Analyze {len(transaction_ids)} transactions.

STEP 1: Call get_transaction_aggregated_batch('{transaction_ids_json}') ONCE to get all transaction data.
STEP 2: Analyze all transactions from the returned data.
STEP 3: For each transaction you identify as FRAUDULENT, call report_fraud(transaction_id, reasons) with:
   - transaction_id: The UUID of the fraudulent transaction
   - reasons: A comma-separated list of fraud indicators (e.g., "account_drained,time_correlation,new_merchant")

CRITICAL RULES:
- Only ONE tool call to get_transaction_aggregated_batch. Use the batch endpoint.
- Call report_fraud() for EACH fraudulent transaction you find (you can call it multiple times)
- If no frauds detected, do NOT call report_fraud() at all
- Do NOT output text - use the report_fraud tool instead"""
    
    runner = LangGraphRunner(agent)
    
    response_text = ''
    tool_calls_count = 0
    fraud_reports = []
    
    try:
        logger.info(f"🔄 Démarrage analyse batch {batch_num} avec {len(transaction_ids)} transactions")
        
        # Créer un message compatible
        user_message = type('Content', (), {
            'parts': [type('Part', (), {'text': user_prompt})()],
            'text': user_prompt
        })()
        
        async def process_events():
            nonlocal response_text, tool_calls_count, fraud_reports
            
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                event_type = getattr(event, 'type', type(event).__name__)
                
                # Détecter les tool calls
                if 'tool_call' in event_type.lower() or hasattr(event, 'function_name'):
                    tool_name = getattr(event, 'function_name', getattr(event, 'name', getattr(event, 'function', None)))
                    tool_calls_count += 1
                    logger.debug(f"🔧 Tool call détecté: {tool_name} (batch {batch_num})")
                    
                    if tool_name == 'report_fraud':
                        args = {}
                        if hasattr(event, 'args'):
                            args = event.args
                        elif hasattr(event, 'arguments'):
                            if isinstance(event.arguments, dict):
                                args = event.arguments
                            elif isinstance(event.arguments, str):
                                try:
                                    args = json.loads(event.arguments)
                                except:
                                    pass
                        
                        if isinstance(args, dict):
                            transaction_id = args.get('transaction_id', '')
                            reasons_str = args.get('reasons', '')
                            if transaction_id:
                                logger.info(f"🚨 Fraude détectée (batch {batch_num}): {transaction_id} - {reasons_str}")
                                fraud_reports.append({
                                    'transaction_id': transaction_id,
                                    'reasons': reasons_str
                                })
                
                # Extraire le texte de réponse
                if hasattr(event, 'text'):
                    response_text += event.text
                elif hasattr(event, 'content'):
                    if hasattr(event.content, 'text'):
                        response_text += event.content.text
                    elif hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text
        
        # Exécuter de manière synchrone
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_events())
        
        response_text = response_text.strip()
        
        frauds_detected = []
        for report in fraud_reports:
            transaction_id = report['transaction_id']
            reasons_str = report['reasons']
            
            reasons = []
            if reasons_str:
                reasons = [r.strip() for r in reasons_str.split(',') if r.strip()]
            
            if transaction_id:
                frauds_detected.append({
                    'transaction_id': transaction_id,
                    'risk_level': 'critical',
                    'risk_score': 100,
                    'reason': '; '.join(reasons) if reasons else 'Fraud detected',
                    'anomalies': reasons if reasons else ['Fraud detected']
                })
        
        batch_end_time = datetime.now()
        batch_duration = (batch_end_time - batch_start_time).total_seconds()
        
        logger.info(
            f"✅ Batch {batch_num} terminé: {len(frauds_detected)} fraudes détectées "
            f"en {batch_duration:.2f}s ({tool_calls_count} tool calls)"
        )
        
        return {
            'batch_num': batch_num,
            'transaction_ids': transaction_ids,
            'frauds_detected': frauds_detected,
            'token_usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'estimated': True
            },
            'duration': batch_duration,
            'response_text': response_text
        }
        
    except Exception as e:
        batch_end_time = datetime.now()
        batch_duration = (batch_end_time - batch_start_time).total_seconds()
        
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.error(
            f"❌ ERREUR dans analyze_batch_with_langgraph_agent (batch {batch_num}):\n"
            f"   Type: {error_type}\n"
            f"   Message: {error_msg}\n"
            f"   Transaction IDs: {transaction_ids}\n"
            f"   Session ID: {session_id}\n"
            f"   Durée: {batch_duration:.2f}s",
            exc_info=True
        )
        
        return {
            'batch_num': batch_num,
            'transaction_ids': transaction_ids,
            'frauds_detected': [],
            'error': error_msg,
            'error_type': error_type,
            'token_usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'estimated': True
            },
            'duration': batch_duration
        }
