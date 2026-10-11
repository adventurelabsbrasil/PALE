# Spec — PALE: Projeto Acústico-Lógico-Estrutural

**Status:** proposta pronta para publicação no tracker  
**Âncora:** entregar um vertical slice local-first no qual uma pessoa cria ou importa um som, acompanha a formação de um universo audiovisual determinístico, aprende as relações entre áudio e visual e pode criar ramificações reversíveis.  
**Seam único:** comando de experiência PALE → artefato versionado de análise/eventos → experiência Three.js local.

## Problem Statement

O usuário quer explorar música de forma audiovisual, científica e lúdica, mas as visualizações musicais tendem a cair em dois extremos: gráficos técnicos que não formam uma experiência ou partículas abstratas que ficam bonitas, porém não permitem entender o que está acontecendo.

Músicas complexas também misturam baixo, percussão, harmonia, melodia, textura, silêncio e efeitos. Se tudo for renderizado como uma única massa, fica difícil distinguir se uma transformação veio de um ataque, de um acorde, de uma nota, de uma distorção, de um ruído ou de uma pausa.

O laboratório já possui ingestão de áudio, análise espectral, experiências locais em Three.js, escultura musical e testes de determinismo, mas ainda não possui uma linha do tempo comum que conecte áudio importado, instrumentos criados pelo usuário, entidades musicais, relações entre vozes, múltiplos universos visuais, explicações didáticas e replay de sessões.

## Solução

Construir uma experiência PALE local-first dentro deste repositório. O comando de experiência recebe WAV ou MP3, analisa o arquivo antes da execução, gera um artefato determinístico e abre uma experiência Three.js.

O áudio e os comandos dos instrumentos sintéticos serão convertidos para uma mesma linha do tempo multiescalar de eventos. Essa linha do tempo alimentará:

- um universo orgânico principal, que se forma lentamente e dança em resposta ao áudio;
- um Observatório Multidomínio sincronizado, que permite inspecionar grave, pulso/impacto, harmonia, melodia/linha, textura/ruído e silêncio/espaço;
- universos alternativos, selecionáveis como lentes experimentais sem reanalisar a música;
- uma camada didática contextual e opcional;
- ramificações reversíveis criadas pela intervenção do usuário.

O pipeline será determinístico para arquivos importados. O mesmo conteúdo, versão do analisador, configuração e seed produzirá a mesma identidade, linha do tempo e resultado visual. Performances ao vivo terão liberdade expressiva, mas poderão ser registradas como sessões reproduzíveis.

MIDI, MusicXML e stems serão adicionados depois como referências opcionais para alinhamento e validação. Quando não existirem, o sistema usará inferências perceptuais com confiança explícita, sem afirmar que identificou exatamente o instrumento ou a intenção musical.

## User Stories

1. Como explorador curioso sem formação musical avançada, quero carregar um WAV ou MP3, para ver a música se transformar em um mundo audiovisual.
2. Como usuário, quero que o sistema analise o arquivo antes de iniciar a experiência, para que o mundo possa ser formado com uma estrutura conhecida e reproduzível.
3. Como usuário, quero ver uma indicação clara do progresso da análise, para saber quando a experiência está pronta.
4. Como usuário, quero carregar o mesmo arquivo novamente e obter o mesmo resultado, para confiar que a música possui uma identidade visual estável.
5. Como usuário, quero acompanhar o áudio em uma linha do tempo, para relacionar momentos da música às transformações do mundo.
6. Como usuário, quero ver o mundo se formar ao longo do tempo, para perceber memória, crescimento, repetição e mudança de estrutura.
7. Como usuário, quero que o mundo dance em tempo real enquanto a música toca, para sentir ataques, pulsos, energia, duração e textura.
8. Como usuário, quero distinguir camadas de grave, pulso/impacto, harmonia, melodia/linha, textura/ruído e silêncio/espaço, para compreender a composição sem depender de rótulos de instrumento.
9. Como usuário, quero selecionar uma entidade persistente, para acompanhar sua trajetória durante a obra.
10. Como usuário, quero visualizar relações entre entidades, para perceber sincronização, repetição, sustentação, tensão, consonância, dissonância e pergunta/resposta.
11. Como usuário, quero ver uma separação entre formação lenta e dança rápida, para distinguir estrutura musical de reação momentânea.
12. Como usuário, quero abrir o Observatório Multidomínio, para inspecionar as mesmas informações que formam o universo orgânico.
13. Como usuário, quero alternar entre o universo orgânico e o Observatório sem reanalisar a música, para comparar diferentes leituras da mesma linha do tempo.
14. Como usuário, quero selecionar mais de um universo para a mesma música, para experimentar interpretações visuais diferentes.
15. Como usuário, quero que todos os universos recebam a mesma linha do tempo, para saber que as diferenças vêm da lente visual e não de análises incompatíveis.
16. Como usuário, quero ver quando uma leitura foi confirmada por uma entrada estruturada, inferida do áudio ou considerada incerta, para interpretar o mundo com honestidade.
17. Como usuário, quero selecionar uma entidade incerta e ver a explicação contextual, para entender quais evidências sustentam aquela inferência.
18. Como usuário, quero consultar forma de onda, espectro, envelope, ataques e energia de um evento, para aprender a relação entre fenômeno acústico e visual.
19. Como usuário, quero ver uma explicação curta quando o mundo muda, para aprender sem abandonar a experiência.
20. Como usuário, quero desligar as explicações, para explorar o universo de maneira livre.
21. Como usuário, quero isolar uma camada em solo, para ouvir e observar o componente selecionado.
22. Como usuário, quero silenciar uma camada, para perceber o que muda no mundo quando uma relação sonora é removida.
23. Como usuário, quero navegar para um momento específico, para investigar uma entrada, pausa, repetição ou mudança de densidade.
24. Como usuário, quero tocar instrumentos sintéticos transparentes, para criar eventos cujo comportamento acústico e visual eu consiga relacionar.
25. Como usuário, quero usar osciladores, baixo, sintetizador, pluck/piano, percussão e ruído/textura, para experimentar diferentes matérias sonoras.
26. Como usuário, quero controlar frequência, envelope, ataque, duração, filtro, ressonância, dinâmica, panorâmica e efeitos, para construir sons com diferentes comportamentos.
27. Como usuário, quero tocar junto com uma faixa carregada, para participar da estrutura existente sem destruí-la.
28. Como usuário, quero adicionar eventos ao mundo durante a reprodução, para criar uma ramificação da obra.
29. Como usuário, quero aproximar, afastar, congelar ou perturbar entidades, para experimentar relações sem alterar o arquivo original.
30. Como usuário, quero que cada intervenção seja registrada como evento, para entender e reproduzir o que fiz.
31. Como usuário, quero salvar uma sessão ao vivo, para reproduzir exatamente minha performance depois.
32. Como usuário, quero voltar à obra original após explorar uma ramificação, para comparar a intervenção com a fonte.
33. Como usuário, quero exportar a linha do tempo e os metadados em JSON, para guardar a experiência e permitir reconstrução.
34. Como usuário, quero receber uma identidade determinística da obra, para distinguir análises e sessões sem depender de um nome humano obrigatório.
35. Como pesquisador, quero registrar hash, versão do analisador, configuração, seed e alinhamento, para reproduzir um resultado.
36. Como pesquisador, quero comparar áudio, MIDI, partitura e stems da mesma obra quando disponíveis, para distinguir invariantes musicais de propriedades do meio.
37. Como pesquisador, quero manter confirmados, inferidos e incertos separados, para não transformar uma hipótese visual em descoberta musical.
38. Como pesquisador, quero comparar universos diferentes sobre a mesma linha do tempo, para estudar quais propriedades cada lente torna salientes.
39. Como pesquisador, quero avaliar sons sintéticos, músicas reais e arquivos do usuário em coortes separadas, para não misturar conclusões incompatíveis.
40. Como desenvolvedor, quero executar a experiência por um comando único, para validar o fluxo ponta a ponta no MacBook Air M4.
41. Como desenvolvedor, quero que a análise não bloqueie a interface, para manter o front responsivo.
42. Como desenvolvedor, quero que o front consuma um contrato versionado de eventos, para trocar renderizadores sem alterar a análise.
43. Como desenvolvedor, quero manter o processamento principal local, para preservar privacidade e permitir uso sem backend público.
44. Como desenvolvedor, quero testar o comportamento pelo seam do artefato gerado, para evitar acoplamento a detalhes internos de DSP ou GPU.

## Decisões de Implementação

### Arquitetura e seam

- A implementação evolui o pacote existente em vez de criar um projeto paralelo.
- O seam de integração é o comando de experiência PALE, que recebe uma entrada, gera um artefato versionado e entrega a experiência local.
- O artefato é autocontido o suficiente para ser servido localmente e contém áudio referenciado/copiado conforme as regras de privacidade, análise, linha do tempo, identidade, configuração e dados de replay.
- O primeiro front será TypeScript + Vite + Three.js direto, aproveitando o controle já existente sobre WebGL, shaders, câmera, áudio e instâncias.
- React, React Three Fiber e Zustand não são requisitos do primeiro corte. Um store explícito pode ser usado, desde que atualizações de alta frequência não provoquem re-renderizações desnecessárias.

### Análise e determinismo

- O núcleo físico reutiliza SoundFile, NumPy e SciPy já presentes no laboratório.
- Librosa só será adicionada quando uma função específica justificar a dependência.
- A análise inicial inclui, no mínimo, energia/RMS, centróide, dispersão espectral, fluxo, ataque, bandas, envelope, estimativa de altura quando confiável, eventos de onset, densidade, silêncio e propriedades temporais.
- Os campos de análise descrevem sinais e inferências; não são rótulos de gênero, emoção, instrumento ou intenção.
- Cada execução registra hash do arquivo original, versão do analisador, versão do contrato, parâmetros, seed, taxa de amostragem, duração e advertências.
- A identidade determinística não depende do nome lexical. O nome algorítmico fica fora da prioridade do MVP e poderá ser adicionado como camada de entretenimento depois.

### Linha do tempo e contrato de eventos

- Áudio importado e comandos ao vivo produzem o mesmo tipo de evento lógico.
- A linha do tempo é multiescalar: microeventos em torno de 20–25 ms, eventos musicais/perceptuais e estruturas maiores como agrupamentos, motivos, ciclos, regiões e frases.
- Um evento deve carregar, conforme disponibilidade, tempo absoluto, duração, camada, energia, frequência/região, ataque, brilho/textura, relações, confiança, origem e identificador estável.
- Entidades persistentes representam vozes ou componentes; relações representam forças e conexões entre elas.
- O contrato diferencia dados confirmados por MIDI/stem/partitura, dados inferidos do áudio e hipóteses de baixa confiança.
- A análise prévia é entregue por REST. WebSocket fica reservado para notas, pads, instrumentos, microfone futuro e ramificações ao vivo.

### Multimodalidade e alinhamento

- O primeiro vertical slice suporta WAV, MP3, instrumentos sintéticos e JSON de sessão/eventos.
- MIDI, MusicXML e stems são a próxima etapa, como referências opcionais e não como substitutos silenciosos da análise do áudio.
- Arquivos da mesma obra são registrados em um manifesto de alinhamento.
- O sistema tenta alinhar automaticamente por ataques, pulsos e duração; o usuário pode corrigir offsets e inserir âncoras manuais.
- O alinhamento mantém tempo absoluto e, quando possível, tempo musical separado.
- Sons sintéticos, músicas reais e arquivos do usuário permanecem em coortes de avaliação distintas.

### Motor audiovisual

- O universo orgânico principal possui uma camada de formação lenta e uma camada de dança rápida.
- Entidades confirmadas, inferidas e incertas têm estabilidade visual diferente, sem esconder a incerteza.
- Grave, pulso/impacto, harmonia, melodia/linha, textura/ruído e silêncio/espaço têm vocabulários visuais distintos, mas não ficam presos a uma única paleta ou metáfora universal.
- Baixo pode formar fundação/território; pulso pode gerar impacto; harmonia pode criar campos/conexões; melodia pode percorrer o espaço; textura pode alterar material; silêncio pode abrir clareiras.
- Esses são mapeamentos de uma lente visual, não afirmações científicas sobre o significado da música.
- O Observatório Multidomínio mostra domínios sincronizados com o universo e permite inspecionar o evento responsável por uma mudança.
- A galeria de universos recebe a mesma linha do tempo e permite comparação; nenhum universo alternativo é tratado como representação principal da verdade musical.

### Interação, áudio e sessões

- O áudio precisa ser carregado/analisado antes da execução do mundo importado.
- A criação ao vivo usa Web Audio API e instrumentos sintéticos transparentes.
- As intervenções alteram uma ramificação, não a obra original.
- Solo, mute, seleção, navegação temporal, congelamento e criação de eventos devem ser reversíveis.
- Uma sessão salva contém a linha do tempo de origem, eventos do usuário, ramificações, estado de universo, seed e versões necessárias para replay.

### Privacidade, execução e publicação futura

- O processamento é local-first no MacBook Air M4.
- Nenhum áudio do usuário é enviado a um serviço remoto no MVP.
- Uma publicação futura na Vercel pode hospedar assets estáticos, mas não deve exigir upload de áudio privado.
- CORS só é necessário quando frontend e servidor local estiverem em origens diferentes; proxy de desenvolvimento ou `CORSMiddleware` pode resolver a separação sem tornar WebSocket obrigatório.
- GLTFExporter fica fora do primeiro corte e será avaliado depois que a geometria e o contrato de eventos estiverem estáveis.

## Decisões de Teste

- O teste principal deve executar o seam completo: entrada controlada → artefato → carregamento da experiência → inspeção do contrato e dos estados observáveis.
- Testar determinismo com o mesmo arquivo, configuração e versão; hashes, eventos, seed e identidade devem ser iguais.
- Testar que alteração de arquivo, configuração ou versão produz identidade distinta e registrada.
- Testar WAV e MP3 válidos, arquivos curtos, silêncio, clipping, estéreo, taxas diferentes e falhas de decodificação.
- Testar que análise prévia concluída produz a mesma linha do tempo que o replay do artefato.
- Testar que áudio importado e eventos sintéticos têm o mesmo contrato lógico.
- Testar que sessões ao vivo podem ser gravadas e reproduzidas sem alterar a obra original.
- Testar que ramificações são reversíveis e não contaminam a linha do tempo canônica.
- Testar que entidades e relações permanecem identificáveis nas seis camadas perceptuais.
- Testar que baixa confiança aparece como incerteza e não como identificação confirmada.
- Testar que o Observatório e o universo orgânico permanecem sincronizados ao navegar, pausar, reiniciar e trocar de universo.
- Testar que a troca de universo não dispara nova análise.
- Testar que pausas preservam espaço visual e que seções densas não viram massa contínua dentro dos limites definidos.
- Testar que a interface continua responsiva durante análise e reprodução em condições representativas do MacBook Air M4.
- Testar limites de entidade, instância, buffer e memória com arquivos curtos e longos.
- Testar exportação e reimportação do JSON de sessão/eventos.
- Usar como prior art os testes existentes de ingestão, contrato de probe, experimento 2 e fase 1; preferir asserções sobre comportamento externo e artefatos verificáveis.
- Os testes científicos posteriores devem manter coortes separadas e não usar rótulos de MIDI, partitura ou stems como entrada do analisador físico quando o objetivo for avaliar inferência a partir do áudio.

## Fora de Escopo

- Treinamento de modelo de machine learning no núcleo do primeiro vertical slice.
- Afirmação de descoberta científica ou de que o visual representa a música de maneira única ou verdadeira.
- Reconhecimento perfeito de instrumentos, acordes, notas ou intenção a partir de um MP3 estéreo.
- Importação inicial de MIDI, MusicXML, stems e imagem/PDF de partitura.
- DAW completa, edição multipista avançada, automação de mixagem e biblioteca extensa de samples.
- Microfone e captura contínua de áudio externo.
- Colaboração remota, contas, armazenamento em nuvem e publicação de áudio privado.
- Backend público, banco vetorial e processamento remoto.
- WebSocket para streaming da análise prévia.
- GLTFExporter e impressão 3D no primeiro corte.
- Nome lexical como requisito do primeiro mundo.
- Variação automática ilimitada de universos, paletas ou shaders.
- Alteração da experiência científica existente sem preservar regressão do Micélio e das experiências atuais.
- Automação diária, evolução autônoma de código e promoção automática de modelos.

## Notas

- O vídeo “John Coltrane - Giant Steps | Visualized on a Mathematical Space”, de Lucio Arese, reforça o uso de domínios sincronizados para vozes diferentes, mas o PALE deve distinguir modo de referência formal e modo de descoberta perceptual. A referência não é especificação do produto.
- O repositório já possui experiências de escultura musical, organismo, probe externo, projeção e análise espectral. O PALE deve aproveitar esses componentes sem misturar suas hipóteses ou declarar que uma visualização estética é evidência científica.
- A primeira hipótese científica fica deliberadamente aberta para a trilha posterior de pesquisa; o vertical slice deve produzir evidência de estabilidade, legibilidade e rastreabilidade antes de testar aprendizagem descoberta.
- O nome lexical, múltiplos mundos avançados, MIDI/MusicXML/stems e modelos aprendidos devem entrar como specs ou tickets separados quando o contrato principal estiver validado.

---

<sub><img src="https://app.adventurelabs.com.br/agents/star-command.png" width="16" height="16" align="top"> Generated with <a href="https://adventurelabs.com.br">Star Command</a> by Adventure Labs · <em>agente: Codex · Star Command</em></sub>
