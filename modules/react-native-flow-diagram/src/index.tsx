import FlowDiagram, {LogLevel} from './NativeFlowDiagram';

export function logSync(msg: string, level: LogLevel) {
  const logLevel = level === LogLevel.DEBUG ? 0.0 : 1.0;
  FlowDiagram.logSync(msg, logLevel);
}
export function logAsync(msg: string, level: LogLevel) {
  const logLevel = level === LogLevel.DEBUG ? 0.0 : 1.0;
  FlowDiagram.logAsync(msg, logLevel);
}
