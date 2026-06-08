#!/usr/bin/env bash
# HAchillesWorld AWS KMS 백업 암호화 확인 스크립트 (M-1 이행)
# 실행: bash scripts/aws_kms_backup_verify.sh
# 필요 조건: AWS CLI 설치 + 적절한 IAM 권한

set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-ap-northeast-2}"
DB_INSTANCE="${HAW_RDS_INSTANCE:-haw-prod-db}"
S3_BUCKET="${HAW_S3_BUCKET:-haw-cold-store}"

echo "=== HAchillesWorld AWS KMS 백업 암호화 점검 (M-1 이행) ==="
echo "리전: $REGION | RDS: $DB_INSTANCE | S3: $S3_BUCKET"
echo "점검일: $(date '+%Y-%m-%d %H:%M KST')"
echo ""

# ── 1. RDS 암호화 및 백업 설정 확인 ──────────────────────────
echo "[1/4] RDS 스토리지 암호화 확인..."
aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE" \
  --region "$REGION" \
  --query 'DBInstances[].[DBInstanceIdentifier,StorageEncrypted,BackupRetentionPeriod,PreferredBackupWindow,MultiAZ]' \
  --output table 2>/dev/null \
  || echo "  ⚠️  RDS 인스턴스를 찾을 수 없거나 권한이 없습니다."

echo ""

# ── 2. RDS KMS 키 확인 ────────────────────────────────────────
echo "[2/4] RDS KMS 키 확인..."
aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE" \
  --region "$REGION" \
  --query 'DBInstances[].KmsKeyId' \
  --output text 2>/dev/null \
  || echo "  ⚠️  KMS 키 조회 실패"

echo ""

# ── 3. 최근 자동 백업 스냅샷 확인 ────────────────────────────
echo "[3/4] 최근 자동 백업 스냅샷 (최근 3개)..."
aws rds describe-db-snapshots \
  --db-instance-identifier "$DB_INSTANCE" \
  --snapshot-type automated \
  --region "$REGION" \
  --query 'reverse(sort_by(DBSnapshots,&SnapshotCreateTime))[:3].[DBSnapshotIdentifier,SnapshotCreateTime,Encrypted,Status]' \
  --output table 2>/dev/null \
  || echo "  ⚠️  자동 백업 스냅샷 조회 실패"

echo ""

# ── 4. S3 버킷 버전 관리 및 암호화 확인 ──────────────────────
echo "[4/4] S3 버킷 버전 관리 및 기본 암호화 확인..."
echo "  버전 관리:"
aws s3api get-bucket-versioning \
  --bucket "$S3_BUCKET" \
  --region "$REGION" 2>/dev/null \
  || echo "    ⚠️  S3 버킷 버전 관리 조회 실패 (버킷명 확인 필요)"

echo "  기본 암호화:"
aws s3api get-bucket-encryption \
  --bucket "$S3_BUCKET" \
  --region "$REGION" 2>/dev/null \
  || echo "    ⚠️  S3 암호화 설정 없음 또는 조회 실패 → SSE-KMS 설정 필요"

echo ""
echo "=== 점검 완료 ==="
echo "결과를 docs/owasp_security_audit_v1.0.md M-1 항목에 기록하세요."
echo ""
echo "미설정 항목 조치 명령:"
echo "  RDS 암호화 미설정:  스냅샷 복원 후 암호화 활성화 인스턴스로 교체 (무중단 불가)"
echo "  S3 버전 관리 미설정: aws s3api put-bucket-versioning --bucket $S3_BUCKET --versioning-configuration Status=Enabled"
echo "  S3 암호화 미설정:   aws s3api put-bucket-encryption --bucket $S3_BUCKET --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\"}}]}'"
