#!/usr/bin/env python3
"""
Script pour normaliser les noms de fichiers dans le dossier dataset.

Supprime les timestamps et numéros des noms de fichiers pour les standardiser.

Usage:
    python scripts/normalize_dataset_files.py [--dry-run]
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()


def normalize_filename(filename: str) -> str:
    """Normalise un nom de fichier en supprimant les timestamps et numéros.
    
    Args:
        filename: Le nom de fichier original
        
    Returns:
        Le nom de fichier normalisé
    """
    # Extraire l'extension
    path = Path(filename)
    stem = path.stem
    extension = path.suffix
    
    # Patterns à supprimer :
    # - Timestamps au format YYYYMMDD_HHMMSS ou YYYYMMDDHHMMSS
    # - Numéros isolés (sauf ceux qui font partie du nom de base)
    
    # Supprimer les timestamps au format _YYYYMMDD_HHMMSS ou _YYYYMMDDHHMMSS
    stem = re.sub(r'_?\d{8}_?\d{6}', '', stem)
    stem = re.sub(r'_?\d{14}', '', stem)  # Format compact YYYYMMDDHHMMSS
    
    # Supprimer les numéros isolés à la fin (comme _1, _2, etc.)
    # mais garder les numéros qui font partie du nom (comme "public 1")
    stem = re.sub(r'_+\d+$', '', stem)
    
    # Nettoyer les underscores multiples
    stem = re.sub(r'_+', '_', stem)
    
    # Supprimer les underscores en début/fin
    stem = stem.strip('_')
    
    # Reconstruire le nom de fichier
    if stem:
        return f"{stem}{extension}"
    else:
        # Si le stem est vide, garder au moins l'extension
        return f"file{extension}"


def find_files_to_rename(dataset_dir: Path) -> List[Tuple[Path, Path]]:
    """Trouve les fichiers qui doivent être renommés.
    
    Args:
        dataset_dir: Le répertoire du dataset
        
    Returns:
        Liste de tuples (ancien_chemin, nouveau_chemin)
    """
    files_to_rename: List[Tuple[Path, Path]] = []
    
    if not dataset_dir.exists():
        return files_to_rename
    
    for file_path in dataset_dir.iterdir():
        if not file_path.is_file():
            continue
        
        old_name = file_path.name
        new_name = normalize_filename(old_name)
        
        # Si le nom a changé, ajouter à la liste
        if old_name != new_name:
            new_path = file_path.parent / new_name
            files_to_rename.append((file_path, new_path))
    
    return files_to_rename


def main() -> None:
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(
        description="Normalise les noms de fichiers dans le dossier dataset"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Affiche les changements sans les appliquer'
    )
    
    args = parser.parse_args()
    
    # Récupérer DATASET_FOLDER depuis .env
    dataset_folder = os.getenv('DATASET_FOLDER', 'public 1')
    project_root = Path(__file__).parent.parent
    dataset_dir = project_root / "dataset" / dataset_folder
    
    print(f"📁 Dossier dataset: {dataset_dir}")
    print(f"📂 Utilisation de DATASET_FOLDER depuis .env: {dataset_folder}")
    
    if not dataset_dir.exists():
        print(f"❌ Erreur: Le dossier n'existe pas: {dataset_dir}")
        exit(1)
    
    # Trouver les fichiers à renommer
    files_to_rename = find_files_to_rename(dataset_dir)
    
    if not files_to_rename:
        print("✅ Aucun fichier à renommer. Tous les fichiers sont déjà normalisés.")
        return
    
    print(f"\n📋 {len(files_to_rename)} fichier(s) à renommer:\n")
    
    # Afficher les changements
    for old_path, new_path in files_to_rename:
        print(f"  📝 {old_path.name}")
        print(f"     → {new_path.name}")
        
        # Vérifier si le fichier de destination existe déjà
        if new_path.exists() and old_path != new_path:
            print(f"     ⚠️  ATTENTION: Le fichier {new_path.name} existe déjà!")
        print()
    
    if args.dry_run:
        print("🔍 Mode dry-run: aucun fichier n'a été renommé.")
        print("💡 Exécutez sans --dry-run pour appliquer les changements.")
        return
    
    # Demander confirmation
    response = input("❓ Continuer avec le renommage? (yes/no): ").strip().lower()
    if response not in ['yes', 'y', 'oui', 'o']:
        print("❌ Renommage annulé")
        return
    
    # Renommer les fichiers
    renamed_count = 0
    errors = []
    
    for old_path, new_path in files_to_rename:
        try:
            # Si le fichier de destination existe déjà et est différent, on ne peut pas renommer
            if new_path.exists() and old_path != new_path:
                errors.append(f"{old_path.name} → {new_path.name} (destination existe déjà)")
                continue
            
            old_path.rename(new_path)
            renamed_count += 1
            print(f"✅ {old_path.name} → {new_path.name}")
            
        except Exception as e:
            errors.append(f"{old_path.name} → {new_path.name} (erreur: {e})")
    
    print(f"\n✅ {renamed_count} fichier(s) renommé(s) avec succès")
    
    if errors:
        print(f"\n⚠️  {len(errors)} erreur(s):")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
