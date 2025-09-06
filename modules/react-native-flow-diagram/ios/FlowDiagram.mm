#import "FlowDiagram.h"
#import "FlowDiagramModule-Swift.h"

@implementation FlowDiagram
RCT_EXPORT_MODULE()

- (std::shared_ptr<facebook::react::TurboModule>)getTurboModule:
    (const facebook::react::ObjCTurboModule::InitParams &)params
{
    return std::make_shared<facebook::react::NativeFlowDiagramSpecJSI>(params);
}

- (void)logAsync:(nonnull NSString *)msg level:(double)level {
    [FlowDiagramUtil logAsyncObjCWithMessage:msg logType:1 logLevel:level];
}

- (void)logSync:(nonnull NSString *)msg level:(double)level { 
    [FlowDiagramUtil logSyncObjCWithMessage:msg logType:1 logLevel:level];
}

@end
