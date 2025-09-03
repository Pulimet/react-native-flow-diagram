package net.alexandroid.flowdiagram

import com.facebook.fbreact.specs.NativeFlowDiagramSpec
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.module.annotations.ReactModule

@ReactModule(name = FlowDiagramModule.NAME)
class FlowDiagramModule(reactContext: ReactApplicationContext) : NativeFlowDiagramSpec(reactContext) {

    companion object {
        const val NAME = "FlowDiagram"
    }

    override fun getName() = NAME

    override fun logSync(msg: String?, level: Double) {
        if (msg == null) {
            return
        }
        val logLevel = if (level == 0.0) LogLevel.DEBUG else LogLevel.INFO
        LogTime.logSync(
            msg,
            LogType.RN,
            logLevel
        )
    }

    override fun logAsync(msg: String?, level: Double) {
        if (msg == null) {
            return
        }
        val logLevel = if (level == 0.0) LogLevel.DEBUG else LogLevel.INFO
        LogTime.logAsync(msg, LogType.RN, logLevel)
    }
}
