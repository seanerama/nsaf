import { portAllocate, portDeallocate, portGetForProject } from './db.js';

export function allocatePorts(projectId, rangeStart, rangeEnd, batchSize = 10) {
  return portAllocate(projectId, rangeStart, rangeEnd, batchSize);
}

export function releasePorts(projectId) {
  portDeallocate(projectId);
}

export function getProjectPorts(projectId) {
  return portGetForProject(projectId);
}
