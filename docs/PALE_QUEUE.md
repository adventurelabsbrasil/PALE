# Fila programada do Codex

O runner `scripts/pale_codex_queue.sh` executa as issues restantes do primeiro corte em ordem estrita:

`#5 → #6 → #7 → #8 → #9`

Cada issue recebe uma sessão Codex fresca. A sessão trabalha na mesma branch de integração, executa testes, cria um commit e encerra. O runner faz push da branch, registra um marcador local e inicia a próxima sessão.

O runner não faz merge. Ao concluir todas as issues, abre um único PR para `main`, permitindo que o Founder revise e faça um merge final.

## Estado e logs

- Branch: `codex/pale-queue`
- Estado local: `artifacts/pale-queue/state/`
- Logs por issue: `artifacts/pale-queue/logs/`
- Lock contra duas filas simultâneas: `artifacts/pale-queue/lock/`

## Ativação

```sh
launchctl bootstrap "gui/$(id -u)" "$PWD/ops/pale-codex-queue.plist"
```

Para interromper a fila sem apagar estado:

```sh
launchctl bootout "gui/$(id -u)/com.adventurelabs.pale-codex-queue"
```

O runner para automaticamente se o worker falhar, deixar mudanças não commitadas, trocar de branch, não criar o commit esperado ou falhar ao publicar a branch.
