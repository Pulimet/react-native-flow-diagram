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

    override fun multiply(a: Double, b: Double) = a * b
}
