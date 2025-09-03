import { TurboModuleRegistry, type TurboModule } from 'react-native';

export enum LogLevel {
  DEBUG,
  INFO
}

export interface Spec extends TurboModule {
  logSync(msg: string, level: number): void;
  logAsync(msg: string, level: number): void;
}

export default TurboModuleRegistry.getEnforcing<Spec>('FlowDiagram');
