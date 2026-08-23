<div align="center">
  <h1>🦖 Dino IA</h1>
  <p><b>Inteligência Artificial jogando e dominando o clássico T-Rex Runner</b></p>

  <p>
    <a href="#-sobre-o-projeto">Sobre</a> •
    <a href="#-funcionalidades">Funcionalidades</a> •
    <a href="#-como-jogar">Como Jogar (Usuários)</a> •
    <a href="#-como-rodar-o-código">Para Desenvolvedores</a> •
    <a href="#-arquiteturas-de-ia">Arquiteturas de IA</a> •
    <a href="#-licença-e-direitos">Licença e Direitos</a>
  </p>
</div>

---

## 📌 Sobre o Projeto

O **Dino IA** é um ambiente de Aprendizado por Reforço e Neuroevolução focado em Inteligência Artificial. Construído em Python puro com Pygame, este simulador foi desenhado para ser ultrarrápido, visualmente agradável e nativamente compatível com algoritmos famosos de Machine Learning como **NEAT**, **DQN** e **PPO**.

Nosso projeto recria o clássico jogo do T-Rex, mas foca em observar agentes de inteligência artificial "aprendendo" a desviar de cactos e pássaros através da tentativa e erro (ou seleção natural)!

> Este é um projeto **Open Source** focado em pesquisa e educação em IA. 🧬

## ✨ Funcionalidades

- **Múltiplos Algoritmos**: Implementações prontas de NEAT (Algoritmo Genético), DQN e PPO.
- **Hub Interativo**: Um menu inicial bonito permitindo escolher qual IA treinar ou assistir.
- **Modo Torneio**: Coloque a melhor rede NEAT, DQN e PPO rodando ao mesmo tempo para ver quem sobrevive mais!
- **Treinamento Ultrarrápido**: Possibilidade de rodar a engine ignorando a taxa de quadros (FPS ilimitado), o que permite às IAs jogarem milhares de partidas em poucos segundos.
- **Modo Bazuca (Dificuldade Extra)**: Incluímos obstáculos novos como "Mísseis" e "Cactos Gigantes" para testar a adaptabilidade da Inteligência.

---

## 🎮 Como Jogar (Apenas Executar)

Se você não quer programar e só quer ver as IAs funcionando ou tentar vencer o dinossauro campeão:

1. Acesse a aba **[Releases](#)** do GitHub.
2. Baixe o arquivo `Dino-IA-Windows-v1.0.0.zip`.
3. Extraia o conteúdo para uma pasta.
4. Clique duas vezes em `DinoIA.exe`.

Nenhuma instalação de Python é necessária!

---

## 💻 Como Rodar o Código (Para Desenvolvedores)

Se você quiser treinar suas próprias IAs ou modificar a engine de física, siga os passos abaixo:

### Pré-requisitos
- Python 3.10+
- Git

### Instalação

```bash
# Clone o repositório
git clone https://github.com/SeuUsuario/dino-ia-final.git
cd dino-ia-final

# (Opcional mas recomendado) Crie um ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### Iniciando o Jogo

```bash
python main.py
```

O Menu Principal será aberto, permitindo interagir, iniciar treinamentos ou carregar *checkpoints* de IAs antigas!

---

## 🧠 Arquiteturas de IA

A engine (`Jogo/dino_env.py`) exporta os estados num formato clássico muito parecido com o OpenAI Gym (uma array com distâncias, tamanhos de inimigos e velocidades), esperando como resposta uma ação discreta: `0 (Correr)`, `1 (Pular)` ou `2 (Abaixar)`.

Neste repositório utilizamos as seguintes abordagens:

1. **NEAT (NeuroEvolution of Augmenting Topologies)**: Utiliza mutações e crossover (algoritmo genético) para evoluir uma população de dinossauros geração após geração.
2. **DQN (Deep Q-Network)**: Treina um único agente através da Equação de Bellman, maximizando a expectativa de recompensas futuras.
3. **PPO (Proximal Policy Optimization)**: Utiliza a biblioteca `stable-baselines3`, o algoritmo State-Of-The-Art para tomada de decisões contínuas/discretas (o mesmo usado em robótica e LLMs como o ChatGPT).

---

## ⚖️ Licença e Direitos

### Licença de Software (Open Source)
O código-fonte deste projeto está licenciado sob a **MIT License**. Sinta-se à vontade para baixar, modificar, distribuir e utilizar em estudos e trabalhos educacionais e comerciais conforme a licença permite. Consulte o arquivo [LICENSE](LICENSE) para ler os termos na íntegra.

### Aviso de Marca (Trademark)
O nome **LabTech**, seus logotipos e toda a sua identidade visual associada **não fazem parte da licença MIT**. Ao realizar forks ou redistribuições, você não deve utilizar a marca LabTech de forma que sugira associação, patrocínio ou endosso oficial por parte da empresa. Projetos derivados devem afirmar no máximo que são "Baseados no projeto da LabTech".

### Aviso de Ativos de Terceiros (Third-Party Notices)
Este repositório contém imagens (sprites) geradas que reproduzem a identidade visual e o design artístico do "Chrome Dino", obra original pertencente à **Google LLC** (Projeto Chromium). A licença MIT presente neste repositório cobre apenas a **arquitetura de software e a inteligência artificial desenvolvida pela LabTech**, e não reivindica direitos autorais sobre a arte dos dinossauros e cactos do Google.
As bibliotecas utilizadas (`pygame`, `torch`, `neat-python`, `stable-baselines3`) pertencem aos seus respectivos criadores e são regidas por suas próprias licenças.

---
<p align="center"><i>Desenvolvido com ☕ por LabTech</i></p>
