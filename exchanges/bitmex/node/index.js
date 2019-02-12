const ws = require("ws");
const subscribeOrderbook =
  "wss://www.bitmex.com/realtime?subscribe=orderBook10:XBTUSD";
//const subscribe1MinTrades = "wss://...?subscribe=tradeBin1m"
const w = new ws(subscribeOrderbook);

w.on("message", data => console.log(data));
