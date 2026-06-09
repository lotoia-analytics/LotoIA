# ADR 001 - Core Architecture

## Contexto

A LotoIA evoluiu para uma plataforma estatística institucional com camadas operacionais, analíticas, de ML governado e de observabilidade.
O projeto precisa preservar modularidade, estabilidade de deploy e separação entre lógica de negócio, persistência e apresentação.

## Problema

Era necessário consolidar uma arquitetura que:

- mantivesse `src/` como núcleo da lógica;
- preservasse a persistência SQLite existente;
- suportasse dashboards institucionais sem quebrar o runtime;
- evitasse refatorações destrutivas;
- permitisse evolução incremental de ML e governança.

## Decisão

Adotar uma arquitetura modular institucional baseada em:

- `src/` para a lógica de negócio;
- `dashboard/` para visualização Streamlit;
- `reports/` para saídas e snapshots;
- `ADRs/` para decisões arquiteturais;
- `tests/` para validação;
- `experiments/` para governança de validação temporal e ML.

## Alternativas Consideradas

1. Centralizar toda a lógica no dashboard.
2. Migrar a persistência para um banco externo.
3. Reorganizar a aplicação em uma arquitetura orientada a serviços.

Essas opções foram rejeitadas por risco de quebra de deploy, aumento de complexidade e perda de rastreabilidade.

## Impacto Arquitetural

- reforço da separação entre apresentação e domínio;
- manutenção do runtime atual;
- preservação do SQLite como persistência operacional;
- facilidade para adicionar novas camadas sem quebrar as existentes.

## Riscos

- crescimento de dependências entre camadas se a disciplina modular não for mantida;
- aumento da complexidade de documentação;
- necessidade de controle rigoroso de compatibilidade entre módulos.

## Benefícios

- evolução incremental com estabilidade;
- auditabilidade;
- rastreabilidade;
- compatibilidade com Streamlit Cloud;
- manutenção da base científica da plataforma.

## Consequências Futuras

- novas camadas devem continuar respeitando a separação modular;
- qualquer expansão deve ser documentada via ADR;
- a arquitetura poderá receber novos módulos analíticos sem ruptura estrutural.

