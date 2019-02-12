const ws = require("ws");
const w = new ws("wss://stream.binance.com:9443/ws/btcusdt@trade");

w.on("open", () => console.log("open stream"));
w.on("close", (code, reason) =>
  console.log(`close code ${code} reason = ${reason}`)
);
w.on("message", msg => console.log(msg));
