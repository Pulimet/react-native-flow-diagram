import type {PropsWithChildren} from 'react';
import React, {useEffect} from 'react';
import {logAsync, logSync} from 'react-native-flow-diagram';
import {
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';

import {
  Colors,
  DebugInstructions,
  Header,
  LearnMoreLinks,
  ReloadInstructions,
} from 'react-native/Libraries/NewAppScreen';
import {LogLevel} from 'react-native-flow-diagram/src/NativeFlowDiagram.ts';

type SectionProps = PropsWithChildren<{
  title: string;
}>;

function Section({children, title}: SectionProps): React.JSX.Element {
  const isDarkMode = useColorScheme() === 'dark';
  return (
    <View style={styles.sectionContainer}>
      <Text
        style={[
          styles.sectionTitle,
          {
            color: isDarkMode ? Colors.white : Colors.black,
          },
        ]}>
        {title}
      </Text>
      <Text
        style={[
          styles.sectionDescription,
          {
            color: isDarkMode ? Colors.light : Colors.dark,
          },
        ]}>
        {children}
      </Text>
    </View>
  );
}

function App(): React.JSX.Element {
  // MainActivity.onCreate -> Start - (Sync Native Example)
  logSync('App.tsx -> Render (Sync RN Example)');
  const isDarkMode = useColorScheme() === 'dark';

  const backgroundStyle = {
    backgroundColor: isDarkMode ? Colors.darker : Colors.lighter,
  };

  const safePadding = '5%';

  useEffect(() => {
    logSync('App.tsx -> useEffect - Start (Sync RN Example)');
    makeNetworkRequest()
    initAsyncLibrary()
    initSyncLibrary()
    logSync('App.tsx -> useEffect - End (Sync RN Example)');
  }, []);

  const makeNetworkRequest = () => {
    fetch('https://jsonplaceholder.typicode.com/todos/1')
      .then(response => {
        if (!response.ok) {
          // Throw an error to be caught by the .catch block
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(json => {
        logAsync('App.tsx -> makeNetworkRequest - Network call successful (Async RN Example)');
        console.log('Fetched data:', json);
      })
      .catch(error => {
        console.error('There was a problem with the fetch operation:', error);
      });
  }

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const initAsyncLibrary = async (): Promise<void> => {
    logAsync("App.tsx -> initAsyncLibrary -> Start - (Async RN Example)");

    // 'await' pauses this function's execution for 2 seconds without blocking
    // the main JavaScript thread, allowing the UI to remain responsive.
    await delay(2000);

    logAsync("App.tsx -> initAsyncLibrary -> End - (Async RN Example)");
  };

  const initSyncLibrary = (): void => {
    logSync("App.tsx -> initSyncLibrary -> Start - (Sync RN Example)");

    // WARNING: This is a blocking operation that will freeze the UI.
    // It's a "busy-wait" loop that consumes 100% CPU on its thread
    // until the time has passed. Avoid this in real applications.
    const start = Date.now();
    while (Date.now() - start < 500) {
      // This loop blocks the entire JavaScript thread.
    }
    logSync("App.tsx -> initSyncLibrary -> End - (Sync RN Example)");
  };

  return (
    <View style={backgroundStyle}>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        backgroundColor={backgroundStyle.backgroundColor}
      />
      <ScrollView style={backgroundStyle}>
        <View style={{paddingRight: safePadding}}>
          <Header />
        </View>
        <View
          style={{
            backgroundColor: isDarkMode ? Colors.black : Colors.white,
            paddingHorizontal: safePadding,
            paddingBottom: safePadding,
          }}>
          <Section title="react-native-flow-diagram">*Testing*:</Section>
          <Section title="Step One">
            Edit <Text style={styles.highlight}>App.tsx</Text> to change this
            screen and then come back to see your edits.
          </Section>
          <Section title="See Your Changes">
            <ReloadInstructions />
          </Section>
          <Section title="Debug">
            <DebugInstructions />
          </Section>
          <Section title="Learn More">
            Read the docs to discover what to do next:
          </Section>
          <LearnMoreLinks />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  sectionContainer: {
    marginTop: 32,
    paddingHorizontal: 24,
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '600',
  },
  sectionDescription: {
    marginTop: 8,
    fontSize: 18,
    fontWeight: '400',
  },
  highlight: {
    fontWeight: '700',
  },
});

export default App;
