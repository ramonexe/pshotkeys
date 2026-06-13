# PSHotkeys

Utilitário Windows para criar atalhos de teclado personalizados que funcionam **apenas quando o Photoshop está aberto** — incluindo ações que não existem nativamente, como rotacionar o canvas com uma tecla.

## Download

**[⬇ Baixar PSHotkeys-Setup.exe](../../releases/latest)**

Execute o installer, siga o wizard e pronto. Não requer Python instalado.

## Funcionalidades

- **Atalhos por perfil** — crie perfis separados para diferentes fluxos de trabalho
- **Detecção automática** — os atalhos só ficam ativos com o Photoshop em foco
- **Ações especiais** — rotação de canvas, stamp visible, toggle de visibilidade e mais
- **Remapeamento** — redirecione qualquer tecla para outro combo
- **JSX customizado** — execute qualquer script ExtendScript diretamente
- **Conflito com PS** — avisa quando um atalho já existe no Photoshop nativamente
- **Tray icon** — roda em segundo plano, toggle ON/OFF pelo ícone na bandeja
- **Startup** — opção de iniciar automaticamente com o Windows

## Interface

Interface dark mode sem barra de título nativa do Windows. Arraste pela barra superior para mover a janela.

## Configuração única no Photoshop

Para ações avançadas (rotação de canvas via ExtendScript):

1. Abra o Photoshop
2. **Editar → Preferências → Geral**
3. Marque **"Permitir que scripts acessem a rede"**
4. Clique OK e reinicie o Photoshop

## Build a partir do código-fonte

```bash
# Instalar dependências
pip install -r requirements.txt

# Gerar o .exe
pyinstaller build.spec --noconfirm

# Gerar o installer (requer Inno Setup 6)
ISCC installer.iss
```

## Antivírus

O PSHotkeys usa hooks globais de teclado (`pynput`) para interceptar teclas enquanto o Photoshop está ativo. Alguns antivírus podem sinalizar isso como suspeito (falso positivo). Se isso acontecer, adicione uma exceção para `PSHotkeys.exe` no seu antivírus.

## Licença

MIT
