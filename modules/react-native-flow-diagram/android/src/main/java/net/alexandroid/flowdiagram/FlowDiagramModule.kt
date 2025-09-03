package net.alexandroid.flowdiagram

import android.util.Log
import com.facebook.fbreact.specs.NativeFlowDiagramSpec
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.module.annotations.ReactModule

@ReactModule(name = FlowDiagramModule.NAME)
class FlowDiagramModule(reactContext: ReactApplicationContext) : NativeFlowDiagramSpec(reactContext) {

    companion object {
        const val NAME = "FlowDiagram"
        private var appLaunchTime = 0L
        fun onApplicationOnCreate() {
            appLaunchTime = System.currentTimeMillis()
            Log.d(NAME, "App has launched - onApplicationOnCreate called in FlowDiagramModule.")
        }

        val loggingInterceptor = LoggingInterceptor()
    }


    override fun getName() = NAME

    override fun multiply(a: Double, b: Double) = a * b
}
