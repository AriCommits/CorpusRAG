"""
Database management utilities for CorpusCallosum.

Provides backup, restore, migration, and export functionality for ChromaDB collections.
"""

import argparse
import json
import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from ..config import load_config
from . import ChromaDBBackend


def _extract_tar_safely(tar: tarfile.TarFile, target_dir: str) -> None:
    """
    Safely extract tar archive members with path traversal validation.

    Prevents Zip Slip (CWE-22) attacks by validating that each extracted
    member is within the target directory.

    Args:
        tar: Open TarFile object
        target_dir: Target directory for extraction

    Raises:
        ValueError: If a member path would escape the target directory
    """
    target_dir = os.path.normpath(os.path.abspath(target_dir))

    for member in tar.getmembers():
        # Resolve the member path
        member_path = os.path.normpath(os.path.abspath(
            os.path.join(target_dir, member.name)
        ))

        # Ensure the resolved path is within target_dir
        if not member_path.startswith(target_dir + os.sep) and member_path != target_dir:
            raise ValueError(
                f"Attempted path traversal detected: member '{member.name}' "
                f"would be extracted to {member_path} (outside {target_dir})"
            )

        tar.extract(member, target_dir)


class DatabaseManager:
    """Database management utilities for CorpusCallosum."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the database manager."""
        self.config = load_config(config_path)
        self.db = ChromaDBBackend(self.config.database)
        self.logger = logging.getLogger(__name__)

    def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            collections = self.db.list_collections()
            self.logger.info(f"Found {len(collections)} collections")
            return collections
        except Exception as e:
            self.logger.error(f"Failed to list collections: {e}")
            raise

    def backup_collection(
        self,
        collection_name: str,
        backup_path: Path,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Backup a single collection to a tar.gz file.
        
        Args:
            collection_name: Name of collection to backup
            backup_path: Path for backup file
            include_metadata: Whether to include collection metadata
            
        Returns:
            Backup summary information
        """
        self.logger.info(f"Starting backup of collection: {collection_name}")
        
        try:
            # Get collection
            collection = self.db.get_collection(collection_name)
            
            # Get all data from collection
            result = collection.get(
                include=["metadatas", "documents", "embeddings"]
            )
            
            # Prepare backup data
            backup_data = {
                "collection_name": collection_name,
                "timestamp": datetime.now().isoformat(),
                "version": "0.5.0",
                "corpus_callosum_version": "0.5.0",
                "total_documents": len(result.get("ids", [])),
                "data": result,
            }
            
            if include_metadata:
                # Include collection metadata if available
                try:
                    collection_info = collection._client.get_collection(collection_name)
                    backup_data["collection_metadata"] = getattr(collection_info, "metadata", {})
                except Exception as e:
                    self.logger.warning(f"Could not get collection metadata: {e}")
            
            # Create backup file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "collection_backup.json"
                
                # Write data to temporary file
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
                # Create compressed archive
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                with tarfile.open(backup_path, "w:gz") as tar:
                    tar.add(temp_path, arcname="collection_backup.json")
            
            summary = {
                "collection_name": collection_name,
                "backup_path": str(backup_path),
                "timestamp": backup_data["timestamp"],
                "total_documents": backup_data["total_documents"],
                "backup_size_bytes": backup_path.stat().st_size,
            }
            
            self.logger.info(f"Backup completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to backup collection {collection_name}: {e}")
            raise

    def restore_collection(
        self,
        backup_path: Path,
        target_collection_name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Restore a collection from backup.
        
        Args:
            backup_path: Path to backup file
            target_collection_name: Optional new name for collection
            overwrite: Whether to overwrite existing collection
            
        Returns:
            Restore summary information
        """
        self.logger.info(f"Starting restore from: {backup_path}")
        
        try:
            # Extract backup data
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(backup_path, "r:gz") as tar:
                    _extract_tar_safely(tar, temp_dir)
                
                backup_file = Path(temp_dir) / "collection_backup.json"
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            # Determine collection name
            collection_name = target_collection_name or backup_data["collection_name"]
            
            # Check if collection exists
            existing_collections = self.list_collections()
            if collection_name in existing_collections:
                if not overwrite:
                    raise ValueError(f"Collection '{collection_name}' already exists. Use --overwrite to replace.")
                else:
                    self.logger.warning(f"Overwriting existing collection: {collection_name}")
                    self.db.delete_collection(collection_name)
            
            # Create collection
            metadata = backup_data.get("collection_metadata", {})
            self.db.create_collection(collection_name, metadata)
            
            # Restore data
            data = backup_data["data"]
            if data.get("ids"):
                self.db.add_documents(
                    collection_name,
                    documents=data.get("documents", []),
                    embeddings=data.get("embeddings", []),
                    metadata=data.get("metadatas", []),
                    ids=data["ids"]
                )
            
            summary = {
                "collection_name": collection_name,
                "backup_timestamp": backup_data["timestamp"],
                "restore_timestamp": datetime.now().isoformat(),
                "documents_restored": len(data.get("ids", [])),
                "source_backup": str(backup_path),
            }
            
            self.logger.info(f"Restore completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to restore from {backup_path}: {e}")
            raise

    def backup_all_collections(
        self,
        backup_dir: Path,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Backup all collections to individual files.
        
        Args:
            backup_dir: Directory for backup files
            include_metadata: Whether to include collection metadata
            
        Returns:
            Summary of all backups
        """
        self.logger.info("Starting full database backup")
        
        collections = self.list_collections()
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summaries = []
        
        for collection_name in collections:
            try:
                backup_path = backup_dir / f"{collection_name}_{timestamp}.tar.gz"
                summary = self.backup_collection(
                    collection_name, backup_path, include_metadata
                )
                summaries.append(summary)
            except Exception as e:
                self.logger.error(f"Failed to backup collection {collection_name}: {e}")
                summaries.append({
                    "collection_name": collection_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        overall_summary = {
            "backup_timestamp": timestamp,
            "total_collections": len(collections),
            "successful_backups": len([s for s in summaries if "error" not in s]),
            "failed_backups": len([s for s in summaries if "error" in s]),
            "backup_directory": str(backup_dir),
            "individual_summaries": summaries,
        }
        
        # Write summary file
        summary_path = backup_dir / f"backup_summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Full backup completed: {overall_summary}")
        return overall_summary

    def export_collection(
        self,
        collection_name: str,
        export_path: Path,
        format: str = "json",
        include_embeddings: bool = False,
    ) -> Dict[str, Any]:
        """
        Export collection data in various formats.
        
        Args:
            collection_name: Name of collection to export
            export_path: Path for export file
            format: Export format (json, csv, jsonl)
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            Export summary information
        """
        self.logger.info(f"Exporting collection {collection_name} to {format}")
        
        try:
            # Get collection data
            collection = self.db.get_collection(collection_name)
            include = ["metadatas", "documents"]
            if include_embeddings:
                include.append("embeddings")
                
            result = collection.get(include=include)
            
            # Prepare export data
            export_data = []
            ids = result.get("ids", [])
            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            embeddings = result.get("embeddings", []) if include_embeddings else []
            
            for i, doc_id in enumerate(ids):
                item = {
                    "id": doc_id,
                    "document": documents[i] if i < len(documents) else None,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
                if include_embeddings and i < len(embeddings):
                    item["embedding"] = embeddings[i]
                
                export_data.append(item)
            
            # Export based on format
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
            elif format.lower() == "jsonl":
                with open(export_path, 'w', encoding='utf-8') as f:
                    for item in export_data:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                        
            elif format.lower() == "csv":
                import csv
                
                if export_data:
                    fieldnames = list(export_data[0].keys())
                    with open(export_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for item in export_data:
                            # Convert complex fields to strings for CSV
                            csv_item = {}
                            for key, value in item.items():
                                if isinstance(value, (dict, list)):
                                    csv_item[key] = json.dumps(value)
                                else:
                                    csv_item[key] = value
                            writer.writerow(csv_item)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            summary = {
                "collection_name": collection_name,
                "export_path": str(export_path),
                "format": format,
                "total_documents": len(export_data),
                "include_embeddings": include_embeddings,
                "export_size_bytes": export_path.stat().st_size,
                "timestamp": datetime.now().isoformat(),
            }
            
            self.logger.info(f"Export completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to export collection {collection_name}: {e}")
            raise

    def migrate_collection(
        self,
        source_collection: str,
        target_collection: str,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Migrate data from one collection to another.
        
        Args:
            source_collection: Source collection name
            target_collection: Target collection name  
            batch_size: Number of documents to process at once
            
        Returns:
            Migration summary information
        """
        self.logger.info(f"Migrating from {source_collection} to {target_collection}")
        
        try:
            # Get source collection
            source = self.db.get_collection(source_collection)
            
            # Create target collection
            if target_collection not in self.list_collections():
                self.db.create_collection(target_collection, {})
            
            # Get all data from source
            result = source.get(
                include=["metadatas", "documents", "embeddings"]
            )
            
            total_docs = len(result.get("ids", []))
            migrated_docs = 0
            
            # Process in batches
            for i in range(0, total_docs, batch_size):
                end_idx = min(i + batch_size, total_docs)
                
                batch_ids = result["ids"][i:end_idx]
                batch_docs = result.get("documents", [])[i:end_idx]
                batch_metadata = result.get("metadatas", [])[i:end_idx]
                batch_embeddings = result.get("embeddings", [])[i:end_idx]
                
                # Add to target collection
                self.db.add_documents(
                    target_collection,
                    documents=batch_docs,
                    embeddings=batch_embeddings,
                    metadata=batch_metadata,
                    ids=batch_ids
                )
                
                migrated_docs += len(batch_ids)
                self.logger.info(f"Migrated {migrated_docs}/{total_docs} documents")
            
            summary = {
                "source_collection": source_collection,
                "target_collection": target_collection,
                "total_documents": total_docs,
                "migrated_documents": migrated_docs,
                "batch_size": batch_size,
                "timestamp": datetime.now().isoformat(),
            }
            
            self.logger.info(f"Migration completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to migrate {source_collection} to {target_collection}: {e}")
            raise


def main():
    """CLI interface for database management utilities."""
    parser = argparse.ArgumentParser(description="CorpusCallosum Database Management")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List collections
    list_parser = subparsers.add_parser("list", help="List all collections")
    
    # Backup collection
    backup_parser = subparsers.add_parser("backup", help="Backup a collection")
    backup_parser.add_argument("collection", help="Collection name")
    backup_parser.add_argument("--output", "-o", required=True, type=Path, help="Backup file path")
    backup_parser.add_argument("--no-metadata", action="store_true", help="Exclude metadata")
    
    # Restore collection
    restore_parser = subparsers.add_parser("restore", help="Restore a collection")
    restore_parser.add_argument("backup_file", type=Path, help="Backup file path")
    restore_parser.add_argument("--name", help="New collection name")
    restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing collection")
    
    # Backup all
    backup_all_parser = subparsers.add_parser("backup-all", help="Backup all collections")
    backup_all_parser.add_argument("--output-dir", "-o", required=True, type=Path, help="Backup directory")
    backup_all_parser.add_argument("--no-metadata", action="store_true", help="Exclude metadata")
    
    # Export collection
    export_parser = subparsers.add_parser("export", help="Export a collection")
    export_parser.add_argument("collection", help="Collection name")
    export_parser.add_argument("--output", "-o", required=True, type=Path, help="Export file path")
    export_parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="Export format")
    export_parser.add_argument("--include-embeddings", action="store_true", help="Include embedding vectors")
    
    # Migrate collection
    migrate_parser = subparsers.add_parser("migrate", help="Migrate a collection")
    migrate_parser.add_argument("source", help="Source collection name")
    migrate_parser.add_argument("target", help="Target collection name") 
    migrate_parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    
    if not args.command:
        parser.print_help()
        return
    
    # Create database manager
    try:
        db_manager = DatabaseManager(args.config)
    except Exception as e:
        print(f"Failed to initialize database manager: {e}")
        return
    
    # Execute command
    try:
        if args.command == "list":
            collections = db_manager.list_collections()
            print(f"\nFound {len(collections)} collections:")
            for collection in collections:
                print(f"  - {collection}")
                
        elif args.command == "backup":
            summary = db_manager.backup_collection(
                args.collection,
                args.output,
                include_metadata=not args.no_metadata
            )
            print(f"Backup completed: {summary}")
            
        elif args.command == "restore":
            summary = db_manager.restore_collection(
                args.backup_file,
                args.name,
                args.overwrite
            )
            print(f"Restore completed: {summary}")
            
        elif args.command == "backup-all":
            summary = db_manager.backup_all_collections(
                args.output_dir,
                include_metadata=not args.no_metadata
            )
            print(f"Full backup completed: {summary}")
            
        elif args.command == "export":
            summary = db_manager.export_collection(
                args.collection,
                args.output,
                args.format,
                args.include_embeddings
            )
            print(f"Export completed: {summary}")
            
        elif args.command == "migrate":
            summary = db_manager.migrate_collection(
                args.source,
                args.target,
                args.batch_size
            )
            print(f"Migration completed: {summary}")
            
    except Exception as e:
        print(f"Command failed: {e}")
        logging.getLogger(__name__).exception("Command execution failed")


if __name__ == "__main__":
    main()