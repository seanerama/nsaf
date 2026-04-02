import { queueDequeue, queuePeek, queueList, projectsByStatus, configGetBool } from './db.js';

export function isPaused() {
  return configGetBool('paused');
}

export function getActiveCount() {
  return projectsByStatus('building').length;
}

export function canDequeue(concurrency) {
  if (isPaused()) return false;
  return getActiveCount() < concurrency;
}

export function dequeueNext() {
  return queueDequeue();
}

export function peekNext() {
  return queuePeek();
}

export function getQueueDepth() {
  return queueList().length;
}
