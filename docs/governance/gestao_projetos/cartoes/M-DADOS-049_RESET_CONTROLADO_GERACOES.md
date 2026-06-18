# M-DADOS-049 — Reset Controlado das Gerações Antigas

| Campo | Valor |
|-------|-------|
| Missão | M-DADOS-049 |
| Tipo | Limpeza controlada operacional / validação recepção |
| Build ADM | `institutional-adm-runtime-v25` |
| Script dry-run | `scripts/ops/m_dados_049_controlled_generation_reset.py` |
| Script validação | `scripts/ops/m_dados_049_post_reset_validation.py` |

## Escopo autorizado

Apagar somente gerações/lotes operacionais antigos e tabelas auxiliares ligadas (`generation_events` deletáveis, `generated_games`, `reconciliation_*`, `institutional_output_signatures`, etc.).

## Preservado

`imported_contests`, histórico oficial, memória científica/institucional, GE 114/115, documentos, LEI15_CORE_002.

## Numeração operacional

Nova fase exibe **Geração 001**, **002**… via rótulo operacional (sem reset perigoso de sequence PostgreSQL).

## Confirmação de execução

```bash
LOTOIA_M_DADOS_049_RESET_CONFIRM=M_DADOS_049_CONTROLLED_RESET \
LOTOIA_M_DADOS_049_BACKUP_CONFIRMED=1 \
python scripts/ops/m_dados_049_controlled_generation_reset.py --execute
```

## Veredicto alvo

**M-DADOS-049 CONCLUÍDA — RESET CONTROLADO EXECUTADO, NOVA FASE OPERACIONAL 001 PRONTA, HISTÓRICO ANALÍTICO E COBERTURA ESTRUTURAL VALIDADOS**
