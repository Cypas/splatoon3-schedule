import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

if __package__:
    from .weapon_matcher import (
        COLLECTION_NAME,
        DEFAULT_DB_PATH,
        DEFAULT_MODEL_DIR,
        DEFAULT_QDRANT_DIR,
        MODEL_NAME,
        WeaponMatcher,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weapon_matcher import (
        COLLECTION_NAME,
        DEFAULT_DB_PATH,
        DEFAULT_MODEL_DIR,
        DEFAULT_QDRANT_DIR,
        MODEL_NAME,
        WeaponMatcher,
    )


def load_documents(db_path: Path) -> tuple[list[dict], list[str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    builds = conn.execute(
        "SELECT id, sendou_name, group_id, is_deco FROM BUILDS ORDER BY id"
    ).fetchall()
    conn.close()
    if len({row["id"] for row in builds}) != len(builds):
        raise ValueError("BUILDS.id 重复")
    if len({row["sendou_name"] for row in builds}) != len(builds):
        raise ValueError("BUILDS.sendou_name 重复")
    if len({(row["group_id"], row["is_deco"]) for row in builds}) != len(builds):
        raise ValueError("BUILDS 中同组贴牌标签重复")
    if any(row["is_deco"] not in (0, 1, 2) for row in builds):
        raise ValueError("BUILDS 存在非法贴牌标签")
    aliases, alias_map, _ = WeaponMatcher(db_path)._load_catalog()
    by_build = {}
    for row in aliases:
        item = by_build.setdefault(row["build_id"], {**row, "aliases": []})
        item["aliases"].append(row["alias"])
    if len(by_build) != len(builds):
        raise ValueError(f"武器元数据不完整: {len(by_build)}/{len(builds)}")
    for alias, rows in alias_map.items():
        if len({row["group_id"] for row in rows}) > 1:
            print(f"跨组别名冲突：{alias} -> {', '.join(row['zh_name'] for row in rows)}")
    labels = {0: "原版", 1: "贴牌", 2: "彩牌或新贴牌"}
    rows = [by_build[build["id"]] for build in builds]
    documents = [
        f"{row['zh_name']}。别名：{'、'.join(row['aliases'])}。{labels[row['tag']]}武器，"
        f"属于{row['weapon_class']}，副武器是{row['sub_name']}，大招是{row['special_name']}。"
        for row in rows
    ]
    return rows, documents


def load_model(model_dir: Path, offline: bool):
    from fastembed import TextEmbedding

    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = model_dir / "model_optimized.onnx"
    if not model_file.exists():
        download_dir = model_dir / ".download"
        model = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(download_dir),
            local_files_only=offline,
            threads=2,
        )
        snapshot = next(download_dir.rglob("model_optimized.onnx"), None)
        if snapshot is None:
            raise FileNotFoundError("下载缓存中未找到 model_optimized.onnx")
        for source in snapshot.parent.iterdir():
            if source.is_file():
                shutil.copy2(source.resolve(), model_dir / source.name)
        del model
        shutil.rmtree(download_dir)
    return TextEmbedding(
        model_name=MODEL_NAME,
        specific_model_path=str(model_dir),
        local_files_only=True,
        threads=2,
    )


def build_vectors(db_path: Path, model_dir: Path, qdrant_dir: Path, offline: bool) -> None:
    from qdrant_client import QdrantClient, models

    rows, documents = load_documents(db_path)
    vectors = list(load_model(model_dir, offline).passage_embed(documents, batch_size=16))
    if len(vectors) != len(rows) or any(len(vector) != 512 for vector in vectors):
        raise ValueError("向量数量或维度错误")
    qdrant_dir.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(qdrant_dir))
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        COLLECTION_NAME,
        vectors_config=models.VectorParams(size=512, distance=models.Distance.COSINE),
    )
    client.upsert(
        COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=row["build_id"],
                vector=vector.tolist(),
                payload={"build_id": row["build_id"], "group_id": row["group_id"], "tag": row["tag"]},
            )
            for row, vector in zip(rows, vectors)
        ],
        wait=True,
    )
    count = client.count(COLLECTION_NAME, exact=True).count
    client.close()
    if count != len(rows):
        raise ValueError(f"Qdrant 点数量错误: {count}/{len(rows)}")
    print(f"Qdrant 索引完成：{count} 个 512 维向量")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--qdrant-dir", type=Path, default=DEFAULT_QDRANT_DIR)
    args = parser.parse_args()
    build_vectors(args.db, args.model_dir, args.qdrant_dir, args.offline)


if __name__ == "__main__":
    main()
