# MakerCraft

Mod de Minecraft 1.21.11, com Fabric, que liga os computadores do mapa a um Arduino de verdade.

## Jogar em outro computador

Não precisa instalar o Arduino IDE.

1. Minecraft 1.21.11, Fabric Loader 0.19.3 ou mais novo, e Fabric API.
2. Copie `makercraft-1.0.0.jar` para a pasta `mods` da instância.
3. Conecte o Arduino pelo USB antes de entrar no mundo. O cabo precisa transmitir dados.
4. Abra o mundo. Na primeira vez, o jogo baixa o gravador e grava a placa sozinho. O chat avisa. Essa primeira gravação usa a internet e pode levar alguns minutos. O gravador fica na pasta `config/makercraft` da instância e não entra no Git.
5. Deixe o monitor serial fechado. A porta fica com o jogo.

Se a placa não aparecer na lista de portas, as placas clonadas usam o driver CH340. Instale esse driver e abra o mundo de novo.

Para gerar o jar: Java 21 e `gradlew build`. O arquivo sai em `build/libs`.

## Dentro do mapa

Clique direito no computador, escreva uma instrução por linha e clique em Executar.

No criativo, o quadrado ao lado da linha tranca essa linha. No sobrevivência, linha trancada não pode ser apagada nem editada.

Clique direito numa saída mostra o número. Agachar com as mãos livres muda esse número.

```
ligar 1
desligar 1
esperar 1000
led ligado
led desligado
quando sinal
senao
fim
repetir
```

O jogo abre mesmo sem o Arduino. Sem a placa, os computadores salvam o texto e não enviam comando.

## Ferramentas do mapa

Os scripts em `tools/` editam um save local. Eles não rodam com o mod. Para apontar para outro mundo, defina a variável `MAKERCRAFT_SAVE` com o caminho da pasta do save.
