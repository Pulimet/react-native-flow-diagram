module.exports = {
  root: true,
  extends: '@react-native',
  // Standalone browser script for the Python CLI's HTML report, not part of the React Native app.
  ignorePatterns: ['modules/react-native-flow-diagram/py/'],
};
