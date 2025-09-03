package com.flowdiagram

import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate
import net.alexandroid.flowdiagram.LogTime
import android.os.Bundle

class MainActivity : ReactActivity() {

    override fun getMainComponentName(): String = "FlowDiagram"

    override fun createReactActivityDelegate(): ReactActivityDelegate =
        DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)

    public override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        LogTime.onIntent(intent)
    }
}
