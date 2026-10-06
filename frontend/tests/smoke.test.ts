import { test } from "node:test";
import assert from "node:assert/strict";

import {
  SMU_ACTIVIDADES_ENDPOINT,
  buildPreventivoAAPayload,
} from "../src/services/smu.service";

test("smoke: el servicio carga con el runner nativo de Node", () => {
  assert.equal(SMU_ACTIVIDADES_ENDPOINT, "/smu/actividades/");
  assert.equal(typeof buildPreventivoAAPayload, "function");
});
