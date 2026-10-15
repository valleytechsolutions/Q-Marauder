# MCU bring-up target

`bridge_probe` is a compileable RouterBridge diagnostic target for
`arduino:zephyr:unoq`. It does not drive any shield GPIO, render a screen, or capture
touch. It is not the final display firmware.

On the board, install the official library and compile:

```sh
arduino-cli lib update-index
# The tested zephyr 0.11.0-rc5 core bundles RouterBridge 0.1.3.
arduino-cli lib install 'MsgPack@0.4.2'
arduino-cli compile --fqbn arduino:zephyr:unoq firmware/bridge_probe
```

Keep the current MCU sketch until the shield pinout and voltage compatibility have
been confirmed. Compilation alone is not proof that RPC transport or display output
works. The first physical milestone is the color-bar test in `docs/DISPLAY.md`.
