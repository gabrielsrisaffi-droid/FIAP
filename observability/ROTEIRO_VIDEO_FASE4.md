# TechChallenge4 — resumo e roteiro do vídeo

Meta: **23 a 24 minutos**, respeitando o limite de 25 minutos registrado no roteiro de entrega. Este arquivo é um guia de fala e gravação, não um texto para leitura integral.

## Situação deste roteiro

Preparado em 16/11/2026, durante a criação da infraestrutura na nova conta AWS Academy. O plano informado tem 43 criações, nenhuma alteração e nenhuma exclusão. A conclusão do apply ainda não foi confirmada.

Já demonstrado na preparação local: cinco serviços instrumentados, métricas e logs, trace distribuído no New Relic com 13 spans e mapa dos cinco serviços, além de abertura e resolução de incidente no PagerDuty com notificações no Discord. A recuperação desse ensaio foi manual.

Ainda depende da validação na AWS: implantação e saúde no EKS, pipeline remoto e imagens finais, dashboards e traces do ambiente de entrega e ciclo completo de recuperação automática. As falas sobre esses resultados só devem ser usadas após comprovação. O nome de apresentação será TechChallenge4; a pasta local será renomeada depois da etapa atual do Terraform.

## Resumo do projeto

O TechChallenge4 evolui o ToggleMaster, uma aplicação de gerenciamento e avaliação de feature flags composta por cinco microsserviços. A solução permite controlar a ativação de funcionalidades por meio de regras, com autenticação e registro de eventos de avaliação.

A Fase 4 acrescenta observabilidade e resposta a incidentes. Métricas, logs e traces permitem acompanhar o funcionamento da aplicação e investigar o caminho de uma requisição entre serviços. Prometheus, Loki e Grafana atendem à monitoração e visualização; OpenTelemetry coleta a telemetria e o New Relic oferece a análise de traces e dependências. PagerDuty gerencia os incidentes e uma integração encaminha suas mudanças de estado ao Discord.

O objetivo final da demonstração é provocar uma falha controlada no serviço de avaliação, observar sua detecção, acompanhar o incidente e comprovar a recuperação automática no Kubernetes. Terraform prepara a infraestrutura; os manifests, Helm e ArgoCD organizam a implantação declarativa. A automação não resolve qualquer falha: ela foi desenhada para o cenário específico demonstrado.

### Abertura sugerida — cerca de 45 segundos

> Olá, somos [nomes dos integrantes], da pós-graduação FIAP. Neste vídeo apresentamos o TechChallenge4, a evolução do projeto ToggleMaster. Nossa aplicação trabalha com feature flags e possui cinco microsserviços. Nesta fase, o foco foi tornar o ambiente observável e preparar uma resposta automatizada a incidentes. Vamos mostrar a arquitetura, as métricas e os logs, o rastreamento de uma requisição e uma demonstração de falha e recuperação. Ao final, apresentaremos as evidências e as principais decisões técnicas.

## Agenda de gravação

| Intervalo | Assunto | Tela principal |
|---|---|---|
| 00:00–01:00 | Apresentação e objetivo | Capa com integrantes e projeto |
| 01:00–03:00 | Arquitetura e fluxo funcional | Diagrama e chamada de avaliação |
| 03:00–05:00 | Infraestrutura e entrega | Terraform, pipeline e ArgoCD |
| 05:00–08:00 | Métricas e logs | Grafana |
| 08:00–11:00 | Trace distribuído e dependências | New Relic |
| 11:00–20:30 | Falha, incidente e recuperação | Terminal, Grafana, PagerDuty e Discord |
| 20:30–23:00 | Evidências, decisões e conclusão | Quadro de resultados e links |
| 23:00–24:00 | Margem para transições | — |

O tempo do incidente é uma reserva de gravação, não uma promessa de recuperação em prazo fixo. Cronometre o ensaio real. Se for necessário cortar esperas, indique o salto de tempo e preserve os horários antes/depois e a identificação do mesmo incidente.

## 1. Arquitetura e fluxo funcional — 01:00 a 03:00

**Mostrar:** diagrama dos cinco serviços, dependências e uma avaliação bem-sucedida com dados de teste.

| Serviço | Responsabilidade a explicar |
|---|---|
| auth-service | Autenticação e validação das credenciais da aplicação |
| flag-service | Gerenciamento e consulta das feature flags |
| targeting-service | Regras que determinam a aplicação de uma flag |
| evaluation-service | Coordenação da avaliação e retorno da decisão |
| analytics-service | Consumo e registro dos eventos de avaliação |

**Fala sugerida:**

> O serviço de avaliação consulta os dados necessários para decidir se uma funcionalidade deve estar ativa. As consultas envolvem os serviços de flags e regras, com validação de autenticação. Os eventos de avaliação seguem por uma fila para processamento pelo serviço de analytics. O cache reduz consultas repetidas; por isso, vamos usar também uma avaliação sem cache para demonstrar as dependências no trace.

Explique PostgreSQL como armazenamento dos serviços correspondentes, Redis como cache, SQS como transporte de eventos e DynamoDB como persistência de analytics. Use o diagrama da implantação efetiva; não descreva o ambiente local como se fosse AWS.

**Transição:** “Com esse fluxo em mente, vamos mostrar como o ambiente é implantado e acompanhado.”

## 2. Infraestrutura e entrega — 03:00 a 05:00

**Mostrar, após validação:**

- Código Terraform e um resumo dos recursos provisionados, sem abrir state ou arquivos de credenciais.
- Uma execução real e concluída do pipeline para o commit apresentado.
- Imagens publicadas e aplicação correspondente no ArgoCD, com revisão e estados de sincronização/saúde visíveis.
- Resumo dos pods e nós do ambiente de entrega.

**Fala sugerida:**

> A infraestrutura é descrita em Terraform, o que facilita sua reprodução e revisão. O processo de entrega valida o código e as imagens antes da publicação. No cluster, usamos configuração declarativa e ArgoCD para acompanhar o estado desejado. A observabilidade é organizada em um chart Helm, com parâmetros específicos para o laboratório.

Mostre o pipeline efetivamente executado. Caso a implantação tenha uma etapa manual, explique-a. Não apresente apenas arquivos de configuração como prova de uma execução bem-sucedida.

## 3. Métricas e logs — 05:00 a 08:00

**Mostrar:** dashboard Grafana com tráfego recente e intervalo de tempo curto e legível.

1. Volume/taxa de requisições: comprovar atividade da aplicação.
2. Erros: apresentar a linha de base antes da falha.
3. CPU e memória: identificar os pods monitorados no EKS.
4. Logs no Loki: abrir um registro recente e explicar serviço, horário e contexto.

**Fala sugerida:**

> As métricas mostram tendências e ajudam a detectar comportamentos anormais. Os logs explicam eventos específicos da aplicação. O Prometheus atende às métricas, o Loki aos logs, e o Grafana reúne a visualização e as regras de alerta. O OpenTelemetry Collector recebe e encaminha a telemetria para os destinos configurados.

Não chame ausência de dados de consumo zero. Se um painel estiver vazio, corrija a coleta antes de gravar. Mostre correlação por trace ID apenas onde ela tiver sido verificada.

## 4. Trace distribuído — 08:00 a 11:00

**Mostrar:** New Relic → evaluation-service → Distributed tracing → uma avaliação com chamadas entre os serviços.

1. Identificar a operação `GET /evaluate`, horário, duração total e erros.
2. Abrir o mapa e identificar os cinco serviços.
3. Expandir as chamadas de regras, flags e autenticação.
4. Mostrar envio do evento, processamento pelo analytics e operação de persistência.

**Fala sugerida:**

> Um trace reúne etapas relacionadas à mesma execução. Cada span representa uma operação, como uma chamada HTTP, o envio de uma mensagem ou uma escrita no banco. Aqui conseguimos acompanhar as dependências e localizar onde o tempo está sendo gasto. A propagação do contexto também permite acompanhar o processamento assíncrono do evento.

Use os valores do trace aberto. O registro local de preparação tinha 13 spans, 18,58 ms e zero erros, mas esses números não devem ser atribuídos ao ensaio AWS. Não some durações de spans sobrepostos como se fossem sequenciais. Não apresente uma marcação de anomalia como erro confirmado sem investigá-la.

## 5. Demonstração do incidente — 11:00 a 20:30

### 5.1 Estado saudável e injeção da falha

**Mostrar:** avaliação HTTP 200, pod atual e início do tráfego de teste. Registrar horário e identificação do pod. Executar somente o procedimento de falha já ensaiado no ambiente de laboratório.

> Agora vamos simular uma falha funcional no serviço de avaliação. A falha causa respostas 503 na operação de avaliação, mantendo o processo e o endpoint de saúde ativos. Isso permite demonstrar a detecção pelo monitoramento e a ação do runbook.

O cenário usa o arquivo temporário `/tmp/togglemaster-fault`, com a opção de injeção habilitada exclusivamente para o ensaio. Os comandos exatos devem ser fechados depois da validação do contexto e dos nomes no EKS.

### 5.2 Detecção e comunicação

**Mostrar:** respostas 503, crescimento de erros, alerta passando por pending e firing, incidente no PagerDuty e mensagem no Discord.

> A regra avalia a taxa de erros durante uma janela de observação. Quando a condição se mantém pelo período configurado, o alerta dispara. O Grafana encaminha o evento ao PagerDuty. A integração de acompanhamento consulta os incidentes e publica suas mudanças de estado no Discord.

Explique o limiar e a duração realmente configurados. A integração com Discord consulta periodicamente; não descreva a notificação como instantânea. Use título, horário e ID para correlacionar as telas.

### 5.3 Recuperação automática

**Mostrar:** recebimento do alerta pelo runbook, registro `restart_requested`, substituição do pod, rollout concluído e nova avaliação HTTP 200.

> O alerta também aciona o runbook de recuperação. Nesse cenário, ele solicita um rollout do deployment de avaliação. O pod substituto não contém o arquivo temporário de falha e a operação volta a responder normalmente. A evidência de recuperação é a combinação do novo pod saudável com uma avaliação bem-sucedida.

Não afirme que o PagerDuty ou o Discord reinicia o serviço: a ação é executada pelo runbook acionado pelo fluxo de alertas. Não reinicie o pod manualmente durante a demonstração de automação. Se for necessário intervir, registre isso e corrija o cenário antes de gravar a versão final.

### 5.4 Resolução e proteção contra repetição

**Mostrar:** tráfego saudável contínuo, redução da taxa de erros, alerta normalizado, incidente resolvido e mensagem de resolução no Discord.

> Após a recuperação, continuamos enviando requisições para que a janela de observação reflita o estado saudável. A resolução se propaga para o incidente e para o canal de comunicação. O runbook usa controles de deduplicação e intervalo entre ações para evitar reinícios repetidos do mesmo evento.

Comprove a proteção com registros e contagem de ações do ensaio. Não confunda demora na limpeza da janela do alerta com aplicação ainda indisponível.

## 6. Resultados e encerramento — 20:30 a 23:00

**Mostrar:** quatro evidências reais: Grafana, trace APM, Discord e execução/resultado do self-healing. Acrescentar commit apresentado e links do repositório e vídeo na entrega.

**Fala sugerida, somente após o teste completo:**

> Demonstramos o caminho da requisição, a detecção de uma falha funcional e a recuperação automática do cenário planejado. As métricas ajudam a detectar, os logs e traces ajudam a investigar, e a gestão de incidentes organiza a comunicação. A automação atua sobre um alvo definido e possui controles para evitar ações repetidas. Como evolução, podemos ampliar os cenários de falha e os critérios de recuperação. O repositório reúne o código, as configurações e as evidências utilizadas nesta apresentação.

Não declarar disponibilidade garantida, ambiente de produção, recuperação de qualquer falha ou melhoria percentual sem medição. Se mencionar tempo de recuperação, informar o intervalo utilizado: primeiro erro até primeiro sucesso, por exemplo. O tempo até o incidente ser resolvido é uma medida distinta.

## Preparação prática da gravação

- Preencher nomes, RMs e usernames exigidos na entrega; confirmar todos os integrantes antes da capa final.
- Manter AWS Academy ativo, serviços saudáveis e tráfego suficiente para preencher os painéis.
- Abrir previamente as abas de Grafana, New Relic, PagerDuty, Discord, ArgoCD, pipeline e terminal.
- Usar fonte legível e poucas abas; gravar um teste curto de áudio e leitura da tela.
- Fechar `.env`, credenciais AWS, chaves, webhooks, arquivos de state e telas de Secrets. Não capturar tokens em comandos ou URLs.
- Usar dados sintéticos. Identificar qualquer evidência local como local.
- Ensaiar o incidente inteiro antes da gravação; confirmar que o resultado é automático e repetível.
- Gravar em blocos, mantendo a sequência e a identificação do incidente no trecho técnico. Reservar a capa e a conclusão definitivas para depois dos testes.
- Se encurtar esperas na edição, colocar “avanço de X minutos” com horários reais; não combinar incidentes diferentes como se fossem um único ciclo.
- Após o ensaio, restaurar a configuração normal sem injeção de falha e verificar saúde.
- Conferir duração, acesso aos links e correspondência entre evidências, commit e ambiente apresentado.

## O que pode ser adiantado durante o provisionamento

Agora: preencher identificação, preparar capa e diagrama, ensaiar a abertura e a explicação da arquitetura, organizar abas e verificar áudio. É possível gravar a introdução e a navegação pelo código, identificando o estágio do projeto.

Depois da validação AWS: gravar dashboard do EKS, trace/mapa do ambiente de entrega, pipeline final, incidente com recuperação automática e conclusão baseada nos resultados observados.

Referências internas: [evidências e requisitos de entrega](EVIDENCIAS.md), [validação técnica](VALIDACAO.md) e [passos operacionais no VS Code](EXECUTAR_NO_VSCODE.md).
