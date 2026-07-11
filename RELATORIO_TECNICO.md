# Relatório Técnico — ToggleMaster  
## Tech Challenge Fase 2 — FIAP

## 1. Introdução

Este relatório apresenta a solução desenvolvida para o Tech Challenge Fase 2 da Pós-graduação FIAP, tendo como objetivo a modernização da aplicação ToggleMaster por meio da adoção de microsserviços, containers, Kubernetes e serviços gerenciados em nuvem.

O ToggleMaster é uma plataforma de gerenciamento e avaliação de feature flags, utilizada para controlar a ativação de funcionalidades em uma aplicação de forma dinâmica, segura e segmentada. A proposta desta fase consistiu em decompor a aplicação em microsserviços, containerizar os serviços, executar o ambiente local com Docker Compose e implantar a solução em ambiente Kubernetes utilizando Amazon EKS, respeitando as limitações do ambiente AWS Academy.

A solução final contempla execução local, infraestrutura em nuvem, orquestração Kubernetes, mensageria com filas, persistência relacional e analítica, cache, escalabilidade automática e exposição externa via Ingress.

## 2. Objetivo da Solução

O principal objetivo da solução foi transformar a aplicação ToggleMaster em uma arquitetura moderna e escalável, baseada em microsserviços independentes. Para isso, foram definidos os seguintes objetivos técnicos:

- Containerizar os cinco microsserviços da aplicação.
- Criar um ambiente local completo com Docker Compose.
- Utilizar bancos PostgreSQL locais para simular a persistência relacional.
- Utilizar Redis para cache.
- Utilizar LocalStack para simulação local do Amazon SQS.
- Utilizar DynamoDB Local para simulação do armazenamento analítico.
- Criar imagens Docker e publicá-las no Amazon ECR.
- Implantar os microsserviços em um cluster Amazon EKS.
- Utilizar Amazon RDS PostgreSQL, ElastiCache Redis, Amazon SQS e Amazon DynamoDB.
- Criar manifests Kubernetes com Deployments, Services, ConfigMaps, Secrets, HPAs e Ingress.
- Configurar probes de saúde e limites de recursos para os containers.
- Validar a comunicação entre os microsserviços e os serviços gerenciados da AWS.

## 3. Arquitetura da Aplicação

A solução foi organizada em cinco microsserviços principais.

### 3.1 auth-service

O `auth-service` é responsável pela autenticação da aplicação, geração e validação de API Keys. Ele utiliza banco PostgreSQL próprio para armazenar as chaves geradas e validar as requisições feitas aos demais serviços.

### 3.2 flag-service

O `flag-service` é responsável pelo cadastro, consulta e manutenção de feature flags. Ele armazena as flags em banco PostgreSQL e depende do `auth-service` para validação das API Keys utilizadas nas chamadas.

### 3.3 targeting-service

O `targeting-service` é responsável pelas regras de segmentação das feature flags. Ele permite definir critérios de avaliação, como regras percentuais, para determinar se uma funcionalidade deve ou não ser habilitada para determinado usuário.

### 3.4 evaluation-service

O `evaluation-service` é responsável por avaliar uma feature flag para um usuário específico. Durante a avaliação, ele consulta o `flag-service`, o `targeting-service`, utiliza Redis para cache e publica eventos de avaliação em uma fila SQS.

### 3.5 analytics-service

O `analytics-service` é responsável por consumir os eventos publicados na fila SQS e gravá-los no DynamoDB. Esse serviço permite armazenar dados analíticos das avaliações realizadas.

## 4. Ambiente Local com Docker Compose

Para viabilizar o desenvolvimento e os testes locais, foi criado um arquivo `docker-compose.yml` responsável por orquestrar todos os microsserviços e suas dependências.

O ambiente local contempla:

- Cinco microsserviços containerizados.
- Dois bancos PostgreSQL locais.
- Redis.
- LocalStack para simulação do Amazon SQS.
- DynamoDB Local.
- Serviço auxiliar `local-init` para criação automática dos recursos locais.

O Docker Compose foi utilizado para orquestração local dos microsserviços e dependências. Já os manifests Kubernetes foram utilizados para implantação no EKS, separando responsabilidades em Deployments, Services, ConfigMaps, Secrets, HPAs e Ingress, com probes e limites de recursos para maior estabilidade e escalabilidade.

A execução local é realizada por meio do comando:

```bash
docker compose up --build
```

Esse comando constrói as imagens dos microsserviços, inicializa os bancos de dados, executa os scripts SQL, sobe Redis, LocalStack, DynamoDB Local e cria automaticamente a fila SQS e a tabela DynamoDB utilizadas pela aplicação.

## 5. Banco de Dados e Inicialização Local

No ambiente local, foram utilizados dois bancos PostgreSQL:

- `auth_db`, utilizado pelo `auth-service`.
- `flags_db`, utilizado pelo `flag-service` e pelo `targeting-service`.

Os scripts SQL foram configurados para execução automática durante a inicialização dos containers PostgreSQL, por meio do diretório `/docker-entrypoint-initdb.d`.

Foram criadas automaticamente as seguintes tabelas:

- `api_keys`
- `flags`
- `targeting_rules`

Além disso, o serviço `local-init` foi criado para automatizar a configuração dos recursos locais simulados da AWS. Esse serviço cria:

- Fila SQS local: `togglemaster-events`.
- Tabela DynamoDB Local: `ToggleMasterAnalytics`.

Essa automação permite que o ambiente local seja reproduzido de forma simples, sem necessidade de configuração manual após o `docker compose up --build`.

## 6. Containerização dos Microsserviços

Cada microsserviço possui seu próprio Dockerfile, permitindo build independente e isolamento das dependências.

Os serviços em Go foram construídos com imagens base adequadas para compilação e execução, enquanto os serviços em Python utilizam ambiente próprio com instalação das dependências via `requirements.txt`.

As imagens foram buildadas localmente e posteriormente publicadas no Amazon ECR, permitindo sua utilização no cluster Kubernetes.

Foram criados repositórios ECR para os seguintes serviços:

- `auth-service`
- `flag-service`
- `targeting-service`
- `evaluation-service`
- `analytics-service`

## 7. Infraestrutura AWS

A implantação em nuvem foi realizada no ambiente AWS Academy, considerando as permissões e limitações da plataforma. Foram utilizados os seguintes serviços:

### 7.1 Amazon ECR

O Amazon ECR foi utilizado para armazenar as imagens Docker dos cinco microsserviços. Após o build local, as imagens foram tagueadas e enviadas para os respectivos repositórios.

### 7.2 Amazon EKS

O Amazon EKS foi utilizado para orquestrar os containers em ambiente Kubernetes. Foi criado um cluster EKS com Managed Node Group, utilizando a role `LabRole`, conforme as permissões disponíveis no AWS Academy.

O cluster recebeu os microsserviços por meio de manifests Kubernetes e utilizou nodes gerenciados para execução dos pods.

### 7.3 Amazon RDS PostgreSQL

Foram criadas três instâncias PostgreSQL para persistência relacional:

- Banco do `auth-service`.
- Banco do `flag-service`.
- Banco do `targeting-service`.

Essa separação reforça a independência entre os microsserviços e reduz o acoplamento entre os domínios da aplicação.

### 7.4 Amazon ElastiCache Redis

O Amazon ElastiCache Redis foi utilizado pelo `evaluation-service` para cache de avaliações e redução de chamadas repetidas aos serviços de flags e targeting.

### 7.5 Amazon SQS

O Amazon SQS foi utilizado como mecanismo de mensageria com filas. O `evaluation-service` publica eventos de avaliação na fila, enquanto o `analytics-service` consome esses eventos para processamento posterior.

### 7.6 Amazon DynamoDB

O Amazon DynamoDB foi utilizado como banco analítico para armazenamento dos eventos de avaliação processados pelo `analytics-service`.

## 8. Kubernetes e Organização dos Manifests

A aplicação foi implantada no Amazon EKS utilizando manifests Kubernetes organizados em uma pasta limpa de entrega chamada `k8s-clean`.

Os manifests contemplam os seguintes recursos:

- Namespace.
- ConfigMap.
- Secrets de exemplo.
- Deployments.
- Services.
- Horizontal Pod Autoscalers.
- Ingress.

A separação dos recursos permite melhor organização, manutenção e reaplicação da infraestrutura Kubernetes.

Os arquivos finais foram validados com:

```bash
kubectl apply --dry-run=client -f k8s-clean
```

Essa validação confirmou que os manifests estavam sintaticamente corretos e prontos para aplicação no cluster.

## 9. ConfigMaps e Secrets

As configurações não sensíveis da aplicação foram armazenadas em um ConfigMap, incluindo URLs internas dos serviços, região AWS, URL da fila SQS e nome da tabela DynamoDB.

As informações sensíveis foram tratadas por meio de Secrets Kubernetes. Entre elas:

- URLs de conexão com os bancos RDS.
- Master Key do serviço de autenticação.
- API Key utilizada entre serviços.
- Credenciais temporárias do AWS Academy.

Para evitar exposição de dados sensíveis no repositório, foi criado um arquivo `02-secrets.example.yaml` contendo apenas placeholders. Os valores reais não foram versionados nos manifests finais.

## 10. Deployments, Services e Probes

Cada microsserviço foi implantado no Kubernetes por meio de um Deployment próprio. Os Deployments definem a imagem Docker, variáveis de ambiente, portas, recursos computacionais e probes de saúde.

Foram configuradas:

- `readinessProbe`: para indicar quando o pod está pronto para receber tráfego.
- `livenessProbe`: para permitir que o Kubernetes reinicie automaticamente containers com falha.

Além disso, foram definidos requests e limits de CPU e memória para cada serviço, contribuindo para melhor controle de recursos no cluster.

Os Services do tipo `ClusterIP` foram utilizados para comunicação interna entre os microsserviços dentro do namespace `togglemaster`.

## 11. Escalabilidade com HPA

Foram configurados Horizontal Pod Autoscalers para os serviços:

- `evaluation-service`
- `analytics-service`

Esses serviços foram escolhidos por estarem diretamente envolvidos no fluxo de avaliação e processamento de eventos, sendo mais propensos a aumento de carga.

Os HPAs foram configurados com:

- Mínimo de 1 réplica.
- Máximo de 3 réplicas.
- Escalonamento baseado em utilização média de CPU de 70%.

Essa configuração permite que o cluster aumente ou reduza automaticamente a quantidade de pods conforme a demanda.

## 12. Exposição Externa com Nginx Ingress

Para exposição externa da aplicação, foi instalado o Nginx Ingress Controller no cluster EKS.

Foi criado um recurso Ingress com rotas para os microsserviços:

- `/auth`
- `/flag`
- `/targeting`
- `/evaluation`
- `/analytics`

O Ingress permite centralizar o acesso externo à aplicação e encaminhar as requisições para os serviços internos correspondentes.

O endpoint externo foi validado por meio do serviço de avaliação, confirmando que a aplicação estava acessível fora do cluster e integrada aos serviços AWS.

## 13. Fluxo de Funcionamento Validado

O fluxo principal validado foi o de avaliação de uma feature flag:

1. Uma API Key é criada no `auth-service`.
2. Uma feature flag é criada no `flag-service`.
3. Uma regra de segmentação é criada no `targeting-service`.
4. O `evaluation-service` recebe uma requisição de avaliação.
5. O `evaluation-service` valida as informações, consulta os serviços internos e utiliza Redis.
6. O resultado da avaliação é retornado ao usuário.
7. Um evento de avaliação é publicado na fila SQS.
8. O `analytics-service` consome o evento da fila.
9. O evento é armazenado no DynamoDB.

Esse fluxo foi validado tanto no ambiente local com Docker Compose quanto no ambiente AWS com EKS e serviços gerenciados.

## 14. Segurança

A solução adotou boas práticas básicas de segurança para o contexto do projeto:

- Separação de configurações sensíveis em Secrets.
- Não versionamento de credenciais reais.
- Uso de Security Groups para controle de acesso aos serviços AWS.
- RDS sem exposição pública.
- Comunicação entre serviços dentro do cluster via Services internos.
- Uso de placeholders em arquivos de exemplo.
- Atualização das credenciais temporárias do AWS Academy quando necessário.

Apesar das limitações do ambiente acadêmico, a solução buscou preservar a separação entre dados sensíveis e configurações públicas.

## 15. Evidências de Funcionamento

Durante o desenvolvimento e implantação, foram validados os seguintes pontos:

- Build dos cinco microsserviços.
- Execução local completa via Docker Compose.
- Inicialização automática dos bancos PostgreSQL locais.
- Criação automática da fila SQS no LocalStack.
- Criação automática da tabela DynamoDB Local.
- Criação das imagens Docker e push para o Amazon ECR.
- Criação do cluster EKS.
- Implantação dos microsserviços no Kubernetes.
- Criação dos Services internos.
- Configuração dos ConfigMaps e Secrets.
- Configuração de probes de saúde.
- Configuração de requests e limits.
- Configuração dos HPAs.
- Instalação do Nginx Ingress Controller.
- Exposição externa da aplicação via Ingress.
- Integração com RDS, ElastiCache Redis, SQS e DynamoDB.
- Persistência de eventos analíticos no DynamoDB.

## 16. Limitações do Ambiente

A implantação foi realizada no ambiente AWS Academy, que possui limitações de permissões, tempo de sessão e créditos disponíveis.

Entre os principais pontos observados:

- Uso obrigatório da role `LabRole`.
- Credenciais temporárias expiram ao reiniciar o laboratório.
- Necessidade de atualizar Secrets com novas credenciais AWS.
- Controle de custos/créditos devido a recursos como EKS, RDS, ElastiCache e Load Balancer.
- Algumas decisões arquiteturais foram adaptadas para respeitar as restrições do ambiente.

Mesmo com essas limitações, foi possível implantar a solução completa e validar o funcionamento dos principais componentes exigidos.

## 17. Estrutura de Arquivos da Entrega

A estrutura principal do projeto ficou organizada da seguinte forma:

```text
TechChallenge2/
├── auth-service/
├── flag-service/
├── targeting-service/
├── evaluation-service/
├── analytics-service/
├── local-init/
├── k8s-clean/
├── k8s-final/
├── docker-compose.yml
├── README.md
└── RELATORIO_TECNICO.md
```

A pasta `k8s-clean` contém os manifests Kubernetes preparados para entrega, sem metadados automáticos e sem credenciais reais.

A pasta `k8s-final` foi mantida como referência dos manifests exportados do ambiente que foi executado no cluster.

## 18. Considerações Finais

O projeto ToggleMaster foi modernizado com sucesso para uma arquitetura baseada em microsserviços, containers e Kubernetes. A solução permitiu separar responsabilidades entre serviços independentes, melhorar a escalabilidade e adotar componentes gerenciados da AWS para persistência, cache e mensageria.

No ambiente local, o Docker Compose permitiu executar toda a aplicação e suas dependências de forma automatizada. No ambiente em nuvem, o Amazon EKS possibilitou a orquestração dos microsserviços, enquanto serviços como Amazon RDS, ElastiCache Redis, SQS e DynamoDB forneceram suporte à persistência, cache, mensageria e armazenamento analítico.

A configuração de HPAs, probes, requests, limits, ConfigMaps, Secrets e Ingress contribuiu para uma implantação mais organizada, controlada e próxima de um ambiente real.

Dessa forma, a solução atende aos objetivos do Tech Challenge Fase 2, demonstrando a aplicação prática de conceitos de DevOps, Cloud, Kubernetes, microsserviços e arquitetura distribuída.

## 19. Conclusão

A entrega final demonstrou a evolução da aplicação ToggleMaster para um modelo baseado em microsserviços e infraestrutura em nuvem. O projeto contemplou desde a execução local com Docker Compose até a implantação no Amazon EKS com integração a serviços gerenciados da AWS.

Foram implementados e validados os principais componentes exigidos para a solução, incluindo containerização, orquestração Kubernetes, banco de dados relacional, cache, mensageria, banco analítico, escalabilidade automática e exposição externa.

Com isso, o projeto evidencia uma arquitetura preparada para crescimento, separação de responsabilidades e operação em ambiente cloud, atendendo aos requisitos propostos para a Fase 2 do Tech Challenge.
