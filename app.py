import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from helpers.config import (
    PROJECT_ROOT, MAX_CONCURRENT_REQUESTS, SAVE_INTERVAL, get_batch_size,
    DATASET_PATH, DATASET_FOLDER
)
from helpers.analysis_state import AnalysisState
from helpers.statistics import calculate_statistics
from helpers.display import display_statistics
from core.runner_setup import setup_runner
from core.batch_analyzer import analyze_batch_with_agent


def find_latest_results_file() -> Optional[Path]:
    """Trouve le fichier de résultats le plus récent."""
    results_dir = PROJECT_ROOT / "scripts" / "results"
    if not results_dir.exists():
        return None
    
    result_files = list(results_dir.glob("transaction_risk_analysis_*.json"))
    if not result_files:
        return None
    
    # Trier par date de modification (le plus récent en premier)
    result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return result_files[0]


def load_failed_transactions(results_file: Path) -> List[str]:
    """Charge les transaction_ids des transactions en erreur."""
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    failed_ids = [
        r.get("transaction_id")
        for r in results
        if isinstance(r, dict) and r.get("risk_level") == "error"
    ]
    
    return failed_ids


def filter_transactions_by_ids(
    transactions: List[Dict[str, Any]], 
    transaction_ids: List[str]
) -> List[Dict[str, Any]]:
    """Filtre les transactions par leurs IDs."""
    id_set = set(transaction_ids)
    return [
        t for t in transactions
        if t.get("transaction_id") in id_set
    ]


def merge_results(
    original_results: List[Dict[str, Any]],
    new_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Fusionne les nouveaux résultats avec les résultats originaux.
    
    Remplace les résultats en erreur par les nouveaux résultats.
    """
    # Créer un dictionnaire pour un accès rapide aux nouveaux résultats
    new_results_by_id = {
        r.get("transaction_id"): r
        for r in new_results
        if isinstance(r, dict) and "transaction_id" in r
    }
    
    merged = []
    for original in original_results:
        transaction_id = original.get("transaction_id")
        
        # Si cette transaction a un nouveau résultat, l'utiliser
        if transaction_id in new_results_by_id:
            merged.append(new_results_by_id[transaction_id])
        else:
            # Sinon, garder le résultat original
            merged.append(original)
    
    return merged


async def retry_failed_transactions(
    results_file: Optional[Path] = None, 
    auto_mode: bool = False
):
    """Retraite toutes les transactions en erreur dans un batch bonus.
    
    Args:
        results_file: Chemin vers le fichier de résultats. Si None, trouve le plus récent.
        auto_mode: Si True, ne demande pas de confirmation et lance automatiquement.
    """
    print("="*70)
    print("🔄 RETRY FAILED TRANSACTIONS (BATCH BONUS)")
    print("="*70)
    
    # Trouver le fichier de résultats le plus récent si non spécifié
    if results_file is None:
        results_file = find_latest_results_file()
        if results_file is None:
            print("❌ Aucun fichier de résultats trouvé dans scripts/results/")
            return
    
    print(f"\n📄 Fichier de résultats: {results_file.name}")
    
    # Charger les transactions en erreur
    failed_ids = load_failed_transactions(results_file)
    
    if not failed_ids:
        print("✅ Aucune transaction en erreur trouvée!")
        return
    
    print(f"❌ {len(failed_ids)} transactions en erreur trouvées")
    
    # Charger le dataset original
    print(f"\n📂 Chargement du dataset: {DATASET_PATH}")
    if not DATASET_PATH.exists():
        print(f"❌ Error: Dataset file not found: {DATASET_PATH}")
        return
    
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        all_transactions = json.load(f)
    
    # Filtrer les transactions en erreur
    failed_transactions = filter_transactions_by_ids(all_transactions, failed_ids)
    
    if len(failed_transactions) != len(failed_ids):
        missing = set(failed_ids) - {t.get("transaction_id") for t in failed_transactions}
        if missing:
            print(f"⚠️  Attention: {len(missing)} transactions en erreur non trouvées dans le dataset")
    
    print(f"✅ {len(failed_transactions)} transactions à retraiter")
    
    # Vérifier les clés API
    openai_api_key = os.getenv('OPENAI_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not openai_api_key and not google_api_key and not openrouter_api_key:
        print("❌ Error: No API key found in .env")
        print("💡 Add OPENROUTER_API_KEY, OPENAI_API_KEY or GOOGLE_API_KEY to your .env file")
        return
    
    if openai_api_key:
        os.environ['OPENAI_API_KEY'] = openai_api_key
    if google_api_key:
        os.environ['GOOGLE_API_KEY'] = google_api_key
    if openrouter_api_key:
        os.environ['OPENROUTER_API_KEY'] = openrouter_api_key
    
    # Demander confirmation seulement si pas en mode automatique
    if not auto_mode:
        print(f"\n⚠️  Vous allez retraiter {len(failed_transactions)} transactions.")
        print("💰 Cela consommera des crédits API!")
        response = input("\n❓ Continuer? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y', 'oui', 'o']:
            print("❌ Analyse annulée")
            return
    else:
        print(f"\n🚀 Retraitement automatique de {len(failed_transactions)} transactions...")
    
    runner = setup_runner()
    
    # Obtenir le modèle utilisé pour calculer la taille de batch appropriée
    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
    batch_size = get_batch_size(model)
    
    print(f"\n{'='*70}")
    print("📊 DÉMARRAGE DU BATCH BONUS")
    print(f"{'='*70}")
    
    start_time = datetime.now()
    user_id = "fraud_analyst_retry"
    
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / "scripts" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    bonus_output_file = results_dir / f"transaction_risk_analysis_bonus_{timestamp}.json"
    
    # Trouver le fichier texte original pour le mettre à jour
    original_timestamp = results_file.stem.replace("transaction_risk_analysis_", "")
    text_output_file = results_dir / f"frauds_{original_timestamp}.txt"
    
    state = AnalysisState(len(failed_transactions), start_time, bonus_output_file, text_output_file)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    print(f"\n⏱️  Analyse démarrée à: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 User ID: {user_id}")
    print(f"🤖 Model: {model}")
    print(f"🔄 Requêtes concurrentes max: {MAX_CONCURRENT_REQUESTS}")
    print(f"📦 Taille du batch: {batch_size} transactions par lot (ajusté pour le modèle)")
    print(f"💾 Fichier de résultats: {bonus_output_file.name}")
    print(f"\n{'─'*70}")
    
    total = len(failed_transactions)
    total_batches = (total + batch_size - 1) // batch_size
    
    # Créer toutes les tâches de batch en parallèle
    batch_tasks = []
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, total)
        batch_transactions = failed_transactions[batch_start:batch_end]
        
        task = analyze_batch_with_agent(
            runner,
            batch_transactions,
            batch_num,
            batch_start,
            state,
            semaphore,
            user_id=user_id
        )
        batch_tasks.append(task)
    
    print(f"\n🚀 Lancement de {total_batches} batches bonus en parallèle (max {MAX_CONCURRENT_REQUESTS} simultanés)...")
    
    # Exécuter tous les batches en parallèle
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
    
    # Vérifier les erreurs
    for batch_num, result in enumerate(batch_results):
        if isinstance(result, Exception):
            print(f"\n❌ Erreur dans le batch bonus {batch_num + 1}: {type(result).__name__}: {str(result)[:200]}")
        else:
            completed = len(state.get_results())
            frauds_count = len([r for r in state.get_results() if r.get("risk_level") in ["high", "critical"]])
            print(f"\n✅ Lot bonus {batch_num + 1}/{total_batches} terminé: {completed}/{total} transactions analysées ({frauds_count} fraudes détectées)")
    
    print(f"\n💾 Fichier texte mis à jour: {text_output_file.name}")
    
    print(f"\n{'─'*70}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    bonus_results = state.get_results()
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH BONUS TERMINÉ!")
    print(f"⏱️  Temps total: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"{'='*70}")
    
    # Le fichier texte est déjà mis à jour en temps réel par AnalysisState
    # Calculer les statistiques pour affichage
    merged_results = bonus_results  # Utiliser les résultats bonus pour les stats
    risk_counts, avg_score, error_count, total_tokens_used, tokens_are_estimated = calculate_statistics(merged_results)
    
    frauds_only = [r for r in merged_results if r.get("risk_level") in ["high", "critical"]]
    print(f"📄 Fichier fraudes mis à jour: {text_output_file.name} ({len(frauds_only)} fraudes au total)")
    
    summary_file = results_dir / f"transaction_analysis_summary_merged_{timestamp}.json"
    summary_data = {
        "analysis_info": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "duration_minutes": duration / 60,
            "total_transactions": len(merged_results),
            "retried_transactions": len(failed_transactions),
            "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
            "throughput_per_second": len(bonus_results) / duration if duration > 0 else 0,
            "average_time_per_transaction": duration / len(bonus_results) if len(bonus_results) > 0 else 0
        },
        "token_usage": {
            "prompt_tokens": total_tokens_used["prompt_tokens"],
            "completion_tokens": total_tokens_used["completion_tokens"],
            "total_tokens": total_tokens_used["total_tokens"],
            "average_tokens_per_transaction": total_tokens_used["total_tokens"] / len(merged_results) if len(merged_results) > 0 else 0,
            "estimated": tokens_are_estimated,
            "note": "Tokens were estimated using approximation formula" if tokens_are_estimated else "Tokens captured from API"
        },
        "risk_distribution": {
            level: {
                "count": count,
                "percentage": (count / len(merged_results)) * 100 if len(merged_results) > 0 else 0
            }
            for level, count in risk_counts.items()
        },
        "scores": {
            "average_risk_score": avg_score,
            "error_count": error_count
        }
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("💾 RÉSULTATS SAUVEGARDÉS")
    print(f"{'='*70}")
    print(f"Fichier fraudes (TXT): {text_output_file.name} ({len(frauds_only)} fraudes)")
    
    display_statistics(merged_results, duration, risk_counts, avg_score, error_count,
                      total_tokens_used, tokens_are_estimated)
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH BONUS COMPLET!")
    print(f"🚨 Fichier fraudes (TXT) mis à jour: {text_output_file.name}")
    print(f"{'='*70}\n")

async def main():
    print("="*70)
    print("🚀 ANALYZING ALL TRANSACTIONS WITH CHALLENGE AGENT")
    print("="*70)

    openai_api_key = os.getenv('OPENAI_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')

    if not openai_api_key and not google_api_key and not openrouter_api_key:
        print("❌ Error: No API key found in .env")
        print("💡 Add OPENROUTER_API_KEY, OPENAI_API_KEY or GOOGLE_API_KEY to your .env file")
        sys.exit(1)

    if openai_api_key:
        os.environ['OPENAI_API_KEY'] = openai_api_key
    if google_api_key:
        os.environ['GOOGLE_API_KEY'] = google_api_key
    if openrouter_api_key:
        os.environ['OPENROUTER_API_KEY'] = openrouter_api_key

    print(f"\n📂 Loading transactions from: {DATASET_PATH}")
    print(f"📁 Dataset folder: {DATASET_FOLDER}")

    if not DATASET_PATH.exists():
        print(f"❌ Error: Dataset file not found: {DATASET_PATH}")
        dataset_dir = PROJECT_ROOT / "dataset"
        if dataset_dir.exists():
            available_folders = [d.name for d in dataset_dir.iterdir() if d.is_dir()]
            if available_folders:
                print(f"💡 Available dataset folders: {', '.join(available_folders)}")
                print(f"💡 Set DATASET_FOLDER in .env file or use: DATASET_FOLDER={available_folders[0]}")
        sys.exit(1)

    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        transactions = json.load(f)

    total = len(transactions)
    print(f"✅ {total} transactions loaded")

    print(f"\n⚠️  You are about to analyze {total} transactions.")
    print("💰 This will consume API credits!")
    response = input("\n❓ Continue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y', 'oui', 'o']:
        print("❌ Analysis cancelled")
        sys.exit(0)

    runner = setup_runner()
    
    # Obtenir le modèle utilisé pour calculer la taille de batch appropriée
    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
    batch_size = get_batch_size(model)

    print(f"\n{'='*70}")
    print("📊 STARTING PARALLEL ANALYSIS")
    print(f"{'='*70}")

    start_time = datetime.now()
    user_id = "fraud_analyst"

    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / "scripts" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_file = results_dir / f"transaction_risk_analysis_{timestamp}.json"
    text_output_file = results_dir / f"frauds_{timestamp}.txt"

    state = AnalysisState(total, start_time, output_file, text_output_file)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    print(f"\n⏱️  Analysis started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 User ID: {user_id}")
    print(f"🤖 Model: {model}")
    print(f"🔄 Max concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"📦 Batch size: {batch_size} transactions per batch (ajusté pour le modèle)")
    print(f"💾 Results file: {output_file.name} (sauvegarde après chaque lot)")
    print(f"💡 Each batch will be analyzed in a single API call")
    print(f"\n{'─'*70}")

    total_batches = (total + batch_size - 1) // batch_size
    
    # Créer toutes les tâches de batch en parallèle
    batch_tasks = []
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, total)
        batch_transactions = transactions[batch_start:batch_end]
        
        task = analyze_batch_with_agent(
            runner,
            batch_transactions,
            batch_num,
            batch_start,
            state,
            semaphore,
            user_id=user_id
        )
        batch_tasks.append(task)
    
    print(f"\n🚀 Lancement de {total_batches} batches en parallèle (max {MAX_CONCURRENT_REQUESTS} simultanés)...")
    
    # Exécuter tous les batches en parallèle
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
    
    # Vérifier les erreurs
    for batch_num, result in enumerate(batch_results):
        if isinstance(result, Exception):
            print(f"\n❌ Erreur dans le batch {batch_num + 1}: {type(result).__name__}: {str(result)[:200]}")
        else:
            completed = len(state.get_results())
            frauds_count = len([r for r in state.get_results() if r.get("risk_level") in ["high", "critical"]])
            print(f"\n✅ Lot {batch_num + 1}/{total_batches} terminé: {completed}/{total} transactions analysées ({frauds_count} fraudes détectées)")
    
    print(f"\n💾 Fichier texte mis à jour: {text_output_file.name}")

    print(f"\n{'─'*70}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results = state.get_results()

    bar_length = 40
    bar = "█" * bar_length
    print(f"\n{'='*70}")
    print(f"📊 Progress: [{bar}] 100.0%")
    print(f"✅ All {total} transactions analyzed!")
    print(f"⏱️  Total time: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"⚡ Speedup: ~{total/(duration/60):.1f} transactions/minute")
    print(f"{'='*70}")

    risk_counts, avg_score, error_count, total_tokens_used, tokens_are_estimated = calculate_statistics(results)

    # Le fichier texte est déjà mis à jour en temps réel
    frauds_only = [r for r in results if r.get("risk_level") in ["high", "critical"]]
    print(f"📄 Fichier fraudes: {text_output_file.name} ({len(frauds_only)} fraudes détectées)")

    print(f"\n{'='*70}")
    print("💾 FINAL RESULTS SAVED")
    print(f"{'='*70}")
    print(f"Frauds file (TXT): {text_output_file.name} ({len(frauds_only)} fraudes)")

    display_statistics(results, duration, risk_counts, avg_score, error_count, 
                      total_tokens_used, tokens_are_estimated)

    print(f"\n{'='*70}")
    print(f"✅ PARALLEL ANALYSIS COMPLETE!")
    print(f"🚨 Frauds (TXT) saved in: {text_output_file.name}")
    print(f"{'='*70}\n")
    
    # Lancer automatiquement le batch bonus si des transactions sont en erreur
    if error_count > 0:
        print(f"\n{'='*70}")
        print(f"🔄 {error_count} transactions en erreur détectées")
        print(f"🚀 Lancement automatique du batch bonus...")
        print(f"{'='*70}\n")
        
        try:
            await retry_failed_transactions(output_file, auto_mode=True)
        except Exception as e:
            print(f"\n❌ Erreur lors du batch bonus: {type(e).__name__}: {str(e)}")
            print(f"💡 Vous pouvez relancer manuellement avec: just retry")
            import traceback
            if os.getenv('DEBUG_ERRORS') == '1':
                traceback.print_exc()
    else:
        print(f"\n✅ Aucune transaction en erreur - pas de batch bonus nécessaire")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "retry":
        # Lancer le batch bonus pour retraiter les transactions en erreur
        results_file = None
        if len(sys.argv) > 2:
            results_file = Path(sys.argv[2])
            if not results_file.exists():
                print(f"❌ Fichier de résultats non trouvé: {results_file}")
                sys.exit(1)
        asyncio.run(retry_failed_transactions(results_file))
    else:
        # Lancer l'analyse normale
        asyncio.run(main())