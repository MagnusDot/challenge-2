import csv
import json
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

def convert_value(value: str, field_name: str) -> Any:

    if not value or value.strip() == "":

        if field_name in ["recipient_id", "payment_method", "sender_iban", 
                          "recipient_iban", "description", "location"]:
            return ""

        if field_name == "balance_after":
            return 0.0
        return ""

    if field_name in ["amount", "balance_after"]:
        try:
            return float(value)
        except ValueError:
            return 0.0

    return value.strip()

def csv_to_json(
    csv_path: Path,
    json_path: Path,
    pretty: bool = False
) -> None:

    if not csv_path.exists():
        raise FileNotFoundError(f"Le fichier CSV n'existe pas: {csv_path}")

    transactions: List[Dict[str, Any]] = []

    print(f"📂 Lecture du fichier CSV: {csv_path}")

    try:
        with open(csv_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)

            expected_fields = {
                'transaction_id', 'sender_id', 'recipient_id',
                'transaction_type', 'amount', 'location',
                'payment_method', 'sender_iban', 'recipient_iban',
                'balance_after', 'description', 'timestamp'
            }

            if not expected_fields.issubset(set(reader.fieldnames or [])):
                missing = expected_fields - set(reader.fieldnames or [])
                raise ValueError(
                    f"Colonnes manquantes dans le CSV: {', '.join(missing)}"
                )

            for row_num, row in enumerate(reader, start=2):
                try:

                    transaction: Dict[str, Any] = {}
                    for field_name, value in row.items():
                        transaction[field_name] = convert_value(value, field_name)

                    transactions.append(transaction)

                except Exception as e:
                    print(f"⚠️  Erreur à la ligne {row_num}: {e}")
                    continue

        print(f"✅ {len(transactions)} transactions lues")

    except Exception as e:
        raise ValueError(f"Erreur lors de la lecture du CSV: {e}")

    json_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 Écriture du fichier JSON: {json_path}")

    indent = 2 if pretty else None
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(
            transactions,
            json_file,
            indent=indent,
            ensure_ascii=False
        )

    print(f"✅ Conversion terminée! {len(transactions)} transactions sauvegardées")
    print(f"📄 Fichier JSON créé: {json_path}")

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Convertit transactions_dataset.csv en JSON"
    )
    parser.add_argument(
        '--input',
        type=str,
        default=None,
        help='Chemin vers le fichier CSV d\'entrée (défaut: utilise DATASET_FOLDER du .env)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Chemin vers le fichier JSON de sortie (défaut: même répertoire que le CSV avec extension .json)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Formate le JSON avec indentation (plus lisible)'
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    if args.input is None:
        dataset_folder = os.getenv('DATASET_FOLDER', 'public 1')
        csv_path = project_root / "dataset" / dataset_folder / "transactions_dataset.csv"
        print(f"📁 Utilisation de DATASET_FOLDER depuis .env: {dataset_folder}")
    else:
        csv_path = project_root / args.input if not Path(args.input).is_absolute() else Path(args.input)

    if args.output:
        json_path = project_root / args.output if not Path(args.output).is_absolute() else Path(args.output)
    else:

        json_path = csv_path.with_suffix('.json')

    try:
        csv_to_json(csv_path, json_path, pretty=args.pretty)
    except FileNotFoundError as e:
        print(f"❌ Erreur: {e}")
        exit(1)
    except ValueError as e:
        print(f"❌ Erreur: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        exit(1)

if __name__ == "__main__":
    main()