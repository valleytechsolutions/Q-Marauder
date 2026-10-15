// Q-Marauder MIT diagnostic target. Deliberately does not initialize shield GPIO.
#include <Arduino_RouterBridge.h>

String lastStatus = "Awaiting verified display profile";

String protocol() {
  return "qm-display/1;probe-only;display=unconfigured";
}

bool status(String text) {
  if (text.length() > 96) return false;
  lastStatus = text;
  return true;
}

void setup() {
  Bridge.begin();
  Bridge.provide_safe("qm.protocol", protocol);
  Bridge.provide_safe("qm.status", status);
}

void loop() {
  // Arduino's Zephyr core services safe callbacks between loop invocations.
  delay(5);
}
