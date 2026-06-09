# ADR — Lei 15A Cartão de Registro da Aposta

## Status

**Accepted**

Registro: `POLITICA_CARTAO_REGISTRO_LEI15A_REGISTRADA`  
Runtime: `RUNTIME_LEI15A_APLICADO_ATE_20D`

---

## Contexto

A plataforma LotoIA opera com duas camadas normativas distintas:

| Camada | Papel | Função |
|--------|-------|--------|
| **Lei 15** | Governança soberana | Gerar base e contexto estatístico- estrutural |
| **Lei 15A** | Operação GP / registro da aposta | Montar o cartão final operacional para registro |

Após o congelamento do núcleo operacional 15D (`ADR_LEI15A_NUCLEO_15D_CONGELADO`) e a
aplicação desse núcleo na faixa inferior do painel institucional, surgiu ambiguidade
operacional: a faixa superior exibe o cartão final da **geração Lei 15**, enquanto a faixa
inferior passou a registrar o cartão montado pela **Lei 15A**.

Sem política explícita, operadores poderiam confundir:

- **reclassificação visual** do cartão final da Lei 15 (rótulos de núcleo / reservas sobre
  a mesma saída gerada); com
- **cartão de registro da aposta** — documento operacional próprio, montado pela Lei 15A a
  partir do núcleo congelado e das reservas auditadas Lei 15A.

Esta ADR elimina essa ambiguidade.

---

## Decisão

### Cartão de registro da aposta

O cartão a ser usado para **registro da aposta** deve ser o **cartão final montado pela
Lei 15A**, e **não** a reclassificação visual do cartão final da Lei 15.

```yaml
cartao_registro_aposta:
  origem: Lei_15A
  regra: nucleo_operacional_GP_congelado + reservas_auditadas_Lei15A
  nao_origem: cartao_final_reclassificado_da_Lei15
```

### Papéis normativos

| Norma | Papel | Função |
|-------|-------|--------|
| **Lei 15** | `governanca_soberana` | `gerar_base/contexto` |
| **Lei 15A** | `operacao_GP_registro_aposta` | `montar_cartao_final_operacional` |

A Lei 15 **não** é substituta do cartão de registro. Sua saída alimenta contexto, geração e
auditoria — mas o registro operacional da aposta obedece à montagem Lei 15A.

### Regra de montagem por formato

| Formato | Composição do cartão de registro Lei 15A |
|---------|------------------------------------------|
| **15D** | `nucleo_lei15A_15D` |
| **16D** | `nucleo_lei15A_15D` + 1 reserva Lei 15A |
| **17D** | `nucleo_lei15A_15D` + 2 reservas Lei 15A |
| **18D** | `nucleo_lei15A_15D` + 3 reservas Lei 15A |
| **19D** | `nucleo_lei15A_15D` + 4 reservas Lei 15A |
| **20D** | `nucleo_lei15A_15D` + `[15, 05, 07, 14, 19]` |
| **21D** | **Pendente Lei 15A** — observacional; runtime bloqueado |
| **22D** | **Observacional** — fora do registro operacional de aposta |
| **23D** | **Observacional** — fora do registro operacional de aposta |

**Núcleo congelado 15D:**

```
01 02 03 04 09 10 11 12 13 18 20 22 23 24 25
```

**Reservas prioritárias Lei 15A** (ordem operacional para expansão 16D–21D):

```
15  05  07  14  19
```

### O que **não** equivale a cartão de registro

| Prática | Status |
|---------|--------|
| Exibir rótulos `núcleo_lei_15` / `reservas_auditadas` sobre cartão da geração Lei 15 | **Reclassificação visual** — não é cartão de aposta |
| Copiar `core_numbers` da geração para a faixa inferior como “núcleo operacional” | **Espelhamento indevido** — proibido como registro |
| Usar cartão final superior (Lei 15) como registro sem montagem Lei 15A | **Não conforme** com esta política |

---

## Limites explícitos

Esta ADR é **registro institucional de política**, não change request de runtime:

1. **Lei 15** permanece soberana na geração — **não alterada** por esta ADR.
2. **Geração, expansão runtime, banco, gateway, guardrails e Railway** permanecem
   **inalterados** nesta missão.
4. **21D–23D** permanecem **observacionais/pendentes**; registro bloqueado na faixa inferior
   até ADR dedicado.

---

## Implementação runtime (2026-06-09)

Status: `RUNTIME_LEI15A_APLICADO_ATE_20D`

- Função `build_lei15A_registration_card(format_size)` em `dashboard/institutional_app.py`
- Faixa inferior: cartão de registro Lei 15A para **15D–20D**
- Faixa superior: geração Lei 15 **inalterada**
- **21D–23D**: status `pendente Lei 15A` — registro bloqueado

---

## Consequências

### Positivas

- Fronteira clara entre saída de geração (Lei 15) e cartão de registro (Lei 15A).
- Operadores sabem qual cartão registrar na aposta operacional GP.
- Base normativa para conferência, auditoria e painel institucional.
- 22D/23D explicitamente fora do registro — evita uso indevido.

### Trade-offs

- Cartão de registro Lei 15A pode **divergir** do cartão final exibido na geração Lei 15
  quando reservas ou núcleo operacional diferirem da saída gerada.
- Exige leitura consciente das duas faixas do painel: superior = geração; inferior = registro.

---

## Conformidade

| Requisito | Atendido |
|-----------|----------|
| Política de cartão de registro documentada | Sim |
| ADR específico criado | Este documento |
| Lei 15A monta cartão operacional próprio | Sim |
| Reclassificação visual ≠ cartão de aposta | Sim |
| 22D/23D observacionais | Sim |
| Alteração de código / runtime | **Sim** — faixa inferior 15D–20D (`RUNTIME_LEI15A_APLICADO_ATE_20D`) |
| Alteração Lei 15 | **Não** |
| Deploy produção | **Não** |

---

## Referências

- `docs/governance/LEI_15A_NUCLEO_OPERACIONAL_15D.md`
- `docs/governance/ADR_LEI15A_NUCLEO_15D_CONGELADO.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `AGENTS.md` — posicionamento LotoIA

---

## Histórico

| Data | Autor / agente | Nota |
|------|----------------|------|
| 2026-06-09 | Cloud agent | Registro institucional da política de cartão de registro da aposta Lei 15A |
| 2026-06-09 | Cloud agent | Runtime aplicado na faixa inferior até 20D |
