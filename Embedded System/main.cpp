#include <Wire.h>
#include <MAX30105.h>
#include <ArduinoBLE.h>

// ================================================================
// USER-CONFIGURABLE CONSTANTS
// ================================================================
// Tune these for performance vs. memory vs. BLE stability
const int SAMPLE_RATE            = 200;   // Hz – higher = more detail, but harder on CPU/BLE
const int BUFFER_HEADROOM_SECONDS = 5;    // Seconds of buffer headroom (prevents overflow during BLE delays)
const float CHUNK_SECONDS        = 0.20f; // How much data is sent in one burst (latency vs. overhead trade-off)
const int PACKET_PACING_MS       = 3;     // Small delay between BLE packets – critical for reliability
const int BATCH_SIZE             = 16;    // Samples per BLE packet (must divide CHUNK_SIZE evenly)

// ================================================================
// DERIVED CONSTANTS (do NOT edit)
// ================================================================
const int BUFFER_SIZE   = SAMPLE_RATE * BUFFER_HEADROOM_SECONDS;
const int RAW_CHUNK_SIZE = (int)(SAMPLE_RATE * CHUNK_SECONDS + 0.5f);
const int CHUNK_SIZE     = (RAW_CHUNK_SIZE / BATCH_SIZE) * BATCH_SIZE; // Rounded to multiple of BATCH_SIZE
const int PACKET_SIZE    = 1 + BATCH_SIZE * 8;                         // 1 byte seq + 8 bytes per sample (4 IR + 4 Red)

// ================================================================
// SENSOR & BLE HARDWARE SETTINGS
// ================================================================
const int LED_BRIGHTNESS = 0xF1;   // Max (~50 mA) – reduce if sensor gets hot
const int SAMPLE_AVERAGE = 1;
const int LED_MODE       = 2;      // Red + IR
const int PULSE_WIDTH    = 411;
const int ADC_RANGE      = 16384;

const char* PPG_SERVICE_UUID  = "180D"; // Re-using standard Heart Rate service UUID
const char* COMMAND_CHAR_UUID = "2A37"; // Write 'S' = start, 'P' = pause
const char* DATA_CHAR_UUID    = "2A38";

// ================================================================
// DEBUG SETTINGS
// ================================================================
const int DEBUG_NONE     = 0;
const int DEBUG_INFO     = 1;
const int DEBUG_VERBOSE  = 2;
const int DEBUG_LEVEL    = DEBUG_NONE;   // Set to DEBUG_NONE in production for best performance

// ================================================================
// GLOBAL OBJECTS & RUNTIME STATE
// ================================================================
MAX30105 particleSensor;

BLEService        ppgService(PPG_SERVICE_UUID);
BLECharacteristic commandChar(COMMAND_CHAR_UUID, BLERead | BLEWrite, 1);
BLECharacteristic dataChar   (DATA_CHAR_UUID,    BLENotify, PACKET_SIZE);

// Streaming state
uint8_t  seqNumber = 0;

uint32_t irRingBuffer[BUFFER_SIZE];
uint32_t redRingBuffer[BUFFER_SIZE];
volatile int writeIndex = 0;
int  readIndex  = 0;
volatile int bufferCount = 0;

uint32_t irChunk[CHUNK_SIZE];
uint32_t redChunk[CHUNK_SIZE];

unsigned long streamingStartTime = 0;
unsigned long totalSamplesDuringStream = 0;
bool streaming = false;
bool sensorConfigured = false;

// ================================================================
// DEBUGS / PRINTS
// ================================================================

// Conditional debug printing – completely compiled out when DEBUG_LEVEL = DEBUG_NONE
void debugPrint(int level, const char* msg) {
  if (level <= DEBUG_LEVEL) {
    Serial.print("[");
    Serial.print(millis());
    Serial.print("] ");
    Serial.println(msg);
  }
}

// Always prints a summary at the end of a streaming session (very useful for tuning)
void printStreamingSummary() {
  if (totalSamplesDuringStream == 0) return;

  float elapsedSec = (millis() - streamingStartTime) / 1000.0f;
  float expected   = elapsedSec * SAMPLE_RATE;
  float missed     = expected - totalSamplesDuringStream;
  float missRate   = (expected > 0) ? (missed / expected) * 100.0f : 0.0f;

  Serial.println("\n=== STREAMING SESSION SUMMARY ===");
  Serial.print("Duration: ");          Serial.print(elapsedSec, 1); Serial.println(" s");
  Serial.print("Samples captured: ");  Serial.println(totalSamplesDuringStream);
  Serial.print("Samples expected: ~"); Serial.println((int)expected);
  Serial.print("Samples missed:   ~"); Serial.print((int)missed);
  Serial.print(" ("); Serial.print(missRate, 1); Serial.println("%)");
  Serial.print("Chunks sent: ");       Serial.println(seqNumber);
  Serial.println("================================\n");
}

// ================================================================
// INITIALIZATION FUNCTIONS
// ================================================================

bool initSensor() {
  // Starts I2C communication with the MAX30102/MAX30105
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    debugPrint(DEBUG_INFO, "MAX30102 not found – check wiring!");
    return false;
  }
  debugPrint(DEBUG_INFO, "Sensor initialized");
  return true;
}

void configureSensor() {
  // Applies the high-performance settings defined above
  particleSensor.setup(LED_BRIGHTNESS, SAMPLE_AVERAGE, LED_MODE,
                       SAMPLE_RATE, PULSE_WIDTH, ADC_RANGE);
  particleSensor.clearFIFO();      // Remove any stale data
  sensorConfigured = true;
  debugPrint(DEBUG_INFO, "Sensor configured for 200 Hz streaming");
}

void shutdownSensor() {
  // Saves power when not streaming
  if (sensorConfigured) {
    particleSensor.shutDown();
    sensorConfigured = false;
    debugPrint(DEBUG_INFO, "Sensor shut down (power saving)");
  }
}

bool initBLE() {
  if (!BLE.begin()) {
    debugPrint(DEBUG_INFO, "BLE initialization failed!");
    return false;
  }
  BLE.setLocalName("PPG_Sensor");
  BLE.setAdvertisedService(ppgService);
  ppgService.addCharacteristic(commandChar);
  ppgService.addCharacteristic(dataChar);
  BLE.addService(ppgService);
  BLE.advertise();
  debugPrint(DEBUG_INFO, "BLE advertising started");
  return true;
}

void resetStreamingState() {
  // Called on every new connection – guarantees a clean start
  streaming = false;
  seqNumber = 0;
  writeIndex = readIndex = bufferCount = 0;
  totalSamplesDuringStream = 0;
  debugPrint(DEBUG_INFO, "Streaming state reset");
}

// ================================================================
// SENSOR DATA ACQUISITION
// ================================================================

int pollSensor() {
  // Reads all available samples from the sensor FIFO into the ring buffer
  if (!streaming) return 0;

  particleSensor.check();               // Updates internal FIFO state
  int samplesRead = 0;

  while (particleSensor.available()) {
    uint32_t ir  = particleSensor.getFIFOIR();
    uint32_t red = particleSensor.getFIFORed();
    particleSensor.nextSample();

    if (bufferCount < BUFFER_SIZE) {
      irRingBuffer[writeIndex]  = ir;
      redRingBuffer[writeIndex] = red;
      writeIndex = (writeIndex + 1) % BUFFER_SIZE;
      bufferCount++;
    } else {
      debugPrint(DEBUG_INFO, "BUFFER OVERFLOW");
    }

    samplesRead++;
    totalSamplesDuringStream++;
  }
  return samplesRead;
}

// ================================================================
// DATA TRANSMISSION (CHUNK → BLE PACKETS)
// ================================================================

bool extractChunk() {
  // Moves the oldest CHUNK_SIZE samples from ring buffer → temporary arrays
  if (bufferCount < CHUNK_SIZE) return false;

  for (int i = 0; i < CHUNK_SIZE; i++) {
    irChunk[i]  = irRingBuffer[readIndex];
    redChunk[i] = redRingBuffer[readIndex];
    readIndex = (readIndex + 1) % BUFFER_SIZE;
  }
  bufferCount -= CHUNK_SIZE;
  return true;
}

bool transmitChunk() {
  // Packs one chunk into several BLE packets and sends them
  if (!extractChunk()) return false;
  seqNumber++;
  int numPackets = CHUNK_SIZE / BATCH_SIZE;

  for (int p = 0; p < numPackets; p++) {
    uint8_t packet[PACKET_SIZE];
    packet[0] = seqNumber;                     // Sequence number (helps receiver reorder if needed)

    int idx = 1;
    for (int s = 0; s < BATCH_SIZE; s++) {
      uint32_t ir  = irChunk[p * BATCH_SIZE + s];
      uint32_t red = redChunk[p * BATCH_SIZE + s];

      // Big-endian packing (consistent across platforms)
      packet[idx++] = (ir  >> 24) & 0xFF;
      packet[idx++] = (ir  >> 16) & 0xFF;
      packet[idx++] = (ir  >>  8) & 0xFF;
      packet[idx++] =  ir        & 0xFF;
      packet[idx++] = (red >> 24) & 0xFF;
      packet[idx++] = (red >> 16) & 0xFF;
      packet[idx++] = (red >>  8) & 0xFF;
      packet[idx++] =  red       & 0xFF;
    }

    dataChar.writeValue(packet, PACKET_SIZE);
    delay(PACKET_PACING_MS);                   // Prevents BLE stack overflow
  }


  if (DEBUG_LEVEL >= DEBUG_INFO) {
    Serial.print("Chunk sent, seq = ");
    Serial.println(seqNumber - 1);
  }
  return true;
}

// ================================================================
// BLE COMMAND HANDLING
// ================================================================

bool handleCommands() {
  // Checks if the client wrote to the command characteristic
  if (!commandChar.written()) return false;

  char cmd = commandChar.value()[0];

  if (cmd == 'S' && !streaming) {
    debugPrint(DEBUG_INFO, "Command: START streaming");
    if (!sensorConfigured) configureSensor();
    streaming = true;
    streamingStartTime = millis();
    return true;
  }
  else if (cmd == 'P') {
    debugPrint(DEBUG_INFO, "Command: PAUSE streaming");
    streaming = false;
    printStreamingSummary();          // Always show stats when pausing
    return true;
  }
  return false;
}

// ================================================================
// DISCONNECT / CLEANUP
// ================================================================

void handleDisconnect() {
  // Runs when the central disconnects
  printStreamingSummary();            // Final statistics
  resetStreamingState();
  shutdownSensor();
  BLE.advertise();                    // Ready for next connection
  debugPrint(DEBUG_INFO, "Disconnected - re-advertising");
}

// ================================================================
// Setup and Lopp
// ================================================================

void setup() {
  Serial.begin(115200);
  while (!Serial);            // Remove this line in battery-powered/production builds

  if (!initSensor()) while (1);   // Halt if sensor missing
  if (!initBLE())    while (1);   // Halt if BLE fails
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {                   // PC Host just connected
    resetStreamingState();

    while (central.connected()) {
      handleCommands();            // Check for Start / Pause commands
      pollSensor();                // Fill ring buffer
      transmitChunk();             // Send buffered data
      BLE.poll();                  // processes BLE events, prevents hangs
    }
    handleDisconnect();             // Cleanup & re-advertise
  }
}