# Lastro — modelo de ficha de feature (v0.1, 13/11/2026)

Leia antes de criar ou revisar um `features/<ID>.json`. A ficha é o contrato da feature: diz **o que entregar**, **como provar** e **em que ponto está**.

Os campos e as regras abaixo são uma proposta inicial. O `hx` valida a ficha (seção 4); ajuste este documento junto com o validador.

## 1. Modelo em branco

Copie, troque os valores e remova o que não se aplica. JSON não aceita comentário: as explicações estão na seção 3.

```json
{
  "id": "MOD-00",
  "titulo": "Verbo + comportamento verificável",
  "modulo": "leitura",
  "requisitos": ["RF-XXX-00"],
  "prioridade": "must",
  "onda": 1,
  "essencial": false,
  "estado": "not_started",
  "responsavel": null,
  "depende_de": [],
  "bloqueada_por": null,
  "tipo_verificacao": "comando",
  "criterios": [
    {
      "id": "c1",
      "descricao": "O que precisa ser verdade",
      "exemplo": { "entrada": "valores inventados", "saida": "resultado esperado" }
    }
  ],
  "verificacao": [
    { "criterio": "c1", "comando": "pytest tests/modules/<modulo>/test_<arquivo>.py::test_<nome>" }
  ],
  "evidencia": null
}
```

## 2. Exemplo preenchido

O saldo por código é a regra 4 do `AGENTS.md`. Confira o ID do requisito na versão vigente dos requisitos.

```json
{
  "id": "VAL-01",
  "titulo": "Conferir o saldo do extrato por cálculo",
  "modulo": "validacao",
  "requisitos": ["RF-VAL-01"],
  "prioridade": "must",
  "onda": 1,
  "essencial": true,
  "estado": "not_started",
  "responsavel": "caio",
  "depende_de": ["LEI-02"],
  "bloqueada_por": null,
  "tipo_verificacao": "comando",
  "criterios": [
    {
      "id": "c1",
      "descricao": "Saldo inicial mais a soma das movimentações é igual ao saldo final do extrato",
      "exemplo": {
        "entrada": "saldo inicial 100000, movimentações +25000 e -4050, saldo final 120950 (centavos)",
        "saida": "fecha=true, diferenca=0"
      }
    },
    {
      "id": "c2",
      "descricao": "Quando não fecha, informa a diferença e não segue para classificação",
      "exemplo": {
        "entrada": "mesmo extrato, saldo final 121000",
        "saida": "fecha=false, diferenca=50, classificacao não é chamada"
      }
    }
  ],
  "verificacao": [
    { "criterio": "c1", "comando": "pytest tests/modules/validacao/test_saldo.py::test_saldo_fecha" },
    { "criterio": "c2", "comando": "pytest tests/modules/validacao/test_saldo.py::test_saldo_nao_fecha" }
  ],
  "evidencia": null
}
```

## 3. Campos

| Campo | Para que serve | Quem preenche |
|---|---|---|
| `id` | Identificador curto com prefixo do módulo (`VAL-01`). Igual ao nome do arquivo. | Quem planeja |
| `titulo` | O comportamento em uma frase, verificável. | Quem planeja |
| `modulo` | leitura, validacao, classificacao, perguntas, revisao, exportacao, front, ia, harness. Define dono, revisor e pasta permitida. | Quem planeja |
| `requisitos` | IDs RF-xxx atendidos. Liga a ficha ao documento de requisitos. | Quem planeja |
| `prioridade`, `onda` | `must` ou `should`; onda 1 ou 2. Orienta o corte quando a meta falha. | Líder |
| `essencial` | `true` nas 4 funcionalidades que nunca saem. | Líder |
| `estado` | `not_started`, `in_progress`, `blocked`, `passing`, `regressed`. | **Só o script** |
| `responsavel` | Quem está com a feature. Um só. | Planejamento |
| `depende_de` | Fichas que precisam estar `passing` antes de começar. | Quem planeja |
| `bloqueada_por` | Decisão aberta (`"D-05"`) ou `null`. | Quem planeja |
| `criterios` | O que precisa ser verdade, cada um com exemplo concreto de entrada e saída. | Dono do módulo |
| `verificacao` | Um comando por critério. Só `pytest` e `ruff`. | Dono do módulo |
| `tipo_verificacao` | `comando` (padrão) ou `manual` (exceção, com justificativa no PR). | Quem planeja |
| `evidencia` | Quando e em que commit foi verificada, e o resultado. | **Só o script** |

### Como escrever um bom critério

- **Ruim:** "a leitura de OFX funciona bem". Ninguém prova isso.
- **Bom:** "com `fixtures/ofx/simples.ofx`, o saldo final calculado é 152034 centavos, igual ao do arquivo". Vira um teste direto.
- Cada critério tem **exemplo de entrada e saída**, escrito pelo dono do módulo. Frases soltas como "saldo confere" deixam o teste livre demais.
- Valores em **centavos**, inteiros. Dados sempre inventados.

## 4. O que o `hx` valida

- O `id` é igual ao nome do arquivo; o `estado` é um dos cinco válidos.
- Todo critério tem ao menos uma verificação, e toda verificação aponta para um critério existente.
- Os comandos começam com `pytest` ou `ruff`. Qualquer outro é recusado.
- `depende_de` só cita fichas que existem, sem ciclo.
- `blocked` exige `bloqueada_por`; `in_progress` exige `responsavel`.
- `estado` e `evidencia` só mudam pelo `hx`. Edição à mão é bloqueada na revisão (rubrica, item Verificação).

Mensagem de erro no formato ERRO / MOTIVO / CORREÇÃO.

## 5. O que não colocar

- **Instruções de como implementar.** A ficha diz o quê, não o como.
- **Progresso e histórico.** Vão no `progress/<ID>.md`.
- **Datas e estimativas de horas.** Envelhecem. A meta é por features `passing`.
- **Cópia de requisito inteiro.** Cite o RF-xxx e escreva só o critério.
- **Dado real.** Nem nos exemplos (veja `docs/SECURITY.md`).
- **Campos "para o futuro".** Se ninguém decide nada com o campo, ele não entra.

## 6. Granularidade

Uma feature é um **comportamento verificável que uma pessoa termina em 1 ou 2 sessões**.

Sinais de que está grande demais:
- mais de 4 critérios;
- critérios de módulos diferentes;
- passou de 2 sessões.

Nesses casos, divida em duas fichas, cada uma com seus critérios. Ficha pequena gera PR pequeno e revisão rápida.

Sinais de que está pequena demais: o critério é só um detalhe de outra feature (ex.: "o botão tem 8 px de raio"). Junte à ficha que o contém.

Dois ou três requisitos pequenos podem dividir uma ficha se forem o mesmo comportamento. Um requisito grande pode virar várias fichas.

## 7. Checklist antes de abrir o PR da ficha

- [ ] `id`, `titulo` e `modulo` conferem; o arquivo se chama `<id>.json`
- [ ] Todo critério tem exemplo de entrada e saída, com dado inventado
- [ ] Todo critério tem um comando em `verificacao`, só `pytest` ou `ruff`
- [ ] `depende_de` e `bloqueada_por` conferidos (nenhuma decisão aberta escondida)
- [ ] `estado` em `not_started` e `evidencia` em `null` (quem muda é o script)
- [ ] A feature cabe em 1 ou 2 sessões