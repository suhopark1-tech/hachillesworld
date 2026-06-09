"""HAchillesWorld AWS KMS 백업 암호화 확인 스크립트 (M-1 이행).

실행:
  python scripts/aws_kms_backup_verify.py

자격증명 설정 방법 (둘 중 하나):
  A. 환경변수:
       set AWS_ACCESS_KEY_ID=AKIA...
       set AWS_SECRET_ACCESS_KEY=...
       set AWS_DEFAULT_REGION=ap-northeast-2
  B. ~/.aws/credentials 파일 (aws configure 후 자동 생성)

필요 IAM 권한:
  rds:DescribeDBInstances, rds:DescribeDBSnapshots,
  s3:GetBucketVersioning, s3:GetBucketEncryption
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime

# Windows CP949 터미널 한글/특수문자 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("boto3 미설치. 실행: pip install boto3")
    sys.exit(1)

REGION       = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
DB_INSTANCE  = os.getenv("HAW_RDS_INSTANCE",   "haw-prod-db")
S3_BUCKET    = os.getenv("HAW_S3_BUCKET",       "haw-cold-store")

PASS = "✅ 통과"
FAIL = "❌ 미설정"
WARN = "⚠️  확인 필요"
NA   = "—  (해당 없음 또는 미운영)"

results: dict[str, str] = {}


def section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def check_rds() -> None:
    section("[1/4] RDS 스토리지 암호화 및 백업 설정")
    try:
        rds = boto3.client("rds", region_name=REGION)
        resp = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE)
        db = resp["DBInstances"][0]

        encrypted      = db.get("StorageEncrypted", False)
        kms_key        = db.get("KmsKeyId", "")
        backup_days    = db.get("BackupRetentionPeriod", 0)
        backup_window  = db.get("PreferredBackupWindow", "")
        multi_az       = db.get("MultiAZ", False)
        engine_version = db.get("EngineVersion", "")

        print(f"  인스턴스     : {DB_INSTANCE}")
        print(f"  엔진 버전    : PostgreSQL {engine_version}")
        print(f"  Multi-AZ     : {'활성화' if multi_az else '비활성화'}")
        print(f"  스토리지 암호화: {'활성화' if encrypted else '비활성화'}")
        print(f"  KMS 키       : {kms_key or '없음'}")
        print(f"  백업 보존 기간: {backup_days}일")
        print(f"  백업 윈도우  : {backup_window}")

        results["RDS 암호화"]    = PASS if encrypted else FAIL
        results["RDS KMS 키"]    = PASS if kms_key else FAIL
        results["RDS 백업 보존"] = PASS if backup_days >= 7 else (WARN if backup_days > 0 else FAIL)
        results["RDS Multi-AZ"]  = PASS if multi_az else WARN

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DBInstanceNotFound":
            print(f"  {WARN} 인스턴스 '{DB_INSTANCE}' 없음 (미운영 상태)")
            results["RDS 암호화"] = results["RDS KMS 키"] = results["RDS 백업 보존"] = NA
        else:
            print(f"  {WARN} 오류: {e}")
            results["RDS 암호화"] = results["RDS KMS 키"] = results["RDS 백업 보존"] = WARN


def check_rds_snapshots() -> None:
    section("[2/4] 최근 자동 백업 스냅샷 (최근 3개)")
    try:
        rds = boto3.client("rds", region_name=REGION)
        resp = rds.describe_db_snapshots(
            DBInstanceIdentifier=DB_INSTANCE,
            SnapshotType="automated",
        )
        snaps = sorted(
            resp.get("DBSnapshots", []),
            key=lambda x: x.get("SnapshotCreateTime", datetime.min),
            reverse=True,
        )[:3]

        if not snaps:
            print(f"  {WARN} 자동 백업 스냅샷 없음 (RDS 백업 활성화 필요)")
            results["자동 백업 스냅샷"] = FAIL
            return

        for snap in snaps:
            ts  = snap.get("SnapshotCreateTime", "")
            enc = snap.get("Encrypted", False)
            st  = snap.get("Status", "")
            sid = snap.get("DBSnapshotIdentifier", "")
            print(f"  {sid}")
            print(f"    생성: {ts}  |  암호화: {'✅' if enc else '❌'}  |  상태: {st}")

        all_enc = all(s.get("Encrypted") for s in snaps)
        results["자동 백업 스냅샷"] = PASS if snaps else FAIL
        results["스냅샷 암호화"]   = PASS if all_enc else FAIL

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DBInstanceNotFound":
            print(f"  {NA}")
            results["자동 백업 스냅샷"] = NA
        else:
            print(f"  {WARN} 오류: {e}")
            results["자동 백업 스냅샷"] = WARN


def check_s3_versioning() -> None:
    section("[3/4] S3 버킷 버전 관리")
    try:
        s3 = boto3.client("s3", region_name=REGION)
        resp = s3.get_bucket_versioning(Bucket=S3_BUCKET)
        status = resp.get("Status", "")

        print(f"  버킷         : {S3_BUCKET}")
        print(f"  버전 관리    : {status or '비활성화'}")

        results["S3 버전 관리"] = PASS if status == "Enabled" else FAIL

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchBucket", "AccessDenied"):
            print(f"  {WARN} 버킷 '{S3_BUCKET}' 없음 또는 접근 거부")
            results["S3 버전 관리"] = NA if code == "NoSuchBucket" else WARN
        else:
            print(f"  {WARN} 오류: {e}")
            results["S3 버전 관리"] = WARN


def check_s3_encryption() -> None:
    section("[4/4] S3 버킷 기본 암호화")
    try:
        s3 = boto3.client("s3", region_name=REGION)
        resp = s3.get_bucket_encryption(Bucket=S3_BUCKET)
        rules = resp.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])

        for rule in rules:
            default = rule.get("ApplyServerSideEncryptionByDefault", {})
            algo    = default.get("SSEAlgorithm", "")
            kms_id  = default.get("KMSMasterKeyID", "기본 AWS 관리형 키")
            print(f"  알고리즘     : {algo}")
            print(f"  KMS 키       : {kms_id}")

        is_kms = any(
            r.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm") == "aws:kms"
            for r in rules
        )
        results["S3 암호화 (KMS)"] = PASS if is_kms else (WARN if rules else FAIL)

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ServerSideEncryptionConfigurationNotFoundError":
            print(f"  {FAIL} 기본 암호화 미설정")
            print(f"  조치: aws s3api put-bucket-encryption ...")
            results["S3 암호화 (KMS)"] = FAIL
        elif code == "NoSuchBucket":
            print(f"  {NA} 버킷 없음")
            results["S3 암호화 (KMS)"] = NA
        else:
            print(f"  {WARN} 오류: {e}")
            results["S3 암호화 (KMS)"] = WARN


def print_summary() -> None:
    section("점검 결과 요약")
    all_pass = True
    for item, status in results.items():
        print(f"  {status:<18} {item}")
        if status in (FAIL, WARN):
            all_pass = False

    print()
    if all_pass:
        print("  ✅ 모든 항목 통과 — M-1 이행 완료")
    else:
        fails = [k for k, v in results.items() if v == FAIL]
        warns = [k for k, v in results.items() if v == WARN]
        if fails:
            print(f"  ❌ 즉시 조치 필요: {', '.join(fails)}")
        if warns:
            print(f"  ⚠️  확인 필요: {', '.join(warns)}")

    print()
    print("  결과를 docs/owasp_security_audit_v1.0.md M-1 항목에 기록하세요.")


def main() -> None:
    print("=" * 60)
    print("  HAchillesWorld AWS KMS 백업 암호화 점검 (M-1)")
    print(f"  점검일: {datetime.now().strftime('%Y-%m-%d %H:%M KST')}")
    print(f"  리전: {REGION}  |  RDS: {DB_INSTANCE}  |  S3: {S3_BUCKET}")
    print("=" * 60)

    try:
        # 자격증명 사전 검증
        sts = boto3.client("sts", region_name=REGION)
        identity = sts.get_caller_identity()
        print(f"\n  인증 계정: {identity['Account']} ({identity['Arn']})")
    except NoCredentialsError:
        print("\n  ❌ AWS 자격증명 없음. 아래 중 하나를 설정하세요:")
        print()
        print("  Windows (PowerShell):")
        print("    $env:AWS_ACCESS_KEY_ID     = 'AKIA...'")
        print("    $env:AWS_SECRET_ACCESS_KEY = '...'")
        print("    $env:AWS_DEFAULT_REGION    = 'ap-northeast-2'")
        print("    python scripts/aws_kms_backup_verify.py")
        print()
        print("  또는 AWS CLI로 로그인:")
        print("    aws configure")
        sys.exit(1)
    except ClientError as e:
        print(f"\n  ⚠️  자격증명 오류: {e}")
        sys.exit(1)

    check_rds()
    check_rds_snapshots()
    check_s3_versioning()
    check_s3_encryption()
    print_summary()

    # 결과 JSON 저장
    out_path = os.path.join(
        os.path.dirname(__file__),
        f"../docs/aws_kms_audit_{datetime.now().strftime('%Y%m%d')}.json",
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "checked_at": datetime.now().isoformat(),
                "region": REGION,
                "rds_instance": DB_INSTANCE,
                "s3_bucket": S3_BUCKET,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"  결과 저장: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
