import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Provider as PaperProvider } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Screens
import LoginScreen from './screens/LoginScreen';
import TasksScreen from './screens/TasksScreen';
import CalendarScreen from './screens/CalendarScreen';
import AnalyticsScreen from './screens/AnalyticsScreen';
import TeamScreen from './screens/TeamScreen';
import ProfileScreen from './screens/ProfileScreen';

// Services
import { AuthService } from './services/AuthService';
import { TaskService } from './services/TaskService';
import { CalendarService } from './services/CalendarService';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          switch (route.name) {
            case 'Tasks':
              iconName = 'check-circle';
              break;
            case 'Calendar':
              iconName = 'calendar-today';
              break;
            case 'Analytics':
              iconName = 'analytics';
              break;
            case 'Team':
              iconName = 'groups';
              break;
            case 'Profile':
              iconName = 'person';
              break;
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
      })}
      tabBarOptions={{
        activeTintColor: '#3498db',
        inactiveTintColor: 'gray',
      }}
    >
      <Tab.Screen name="Tasks" component={TasksScreen} />
      <Tab.Screen name="Calendar" component={CalendarScreen} />
      <Tab.Screen name="Analytics" component={AnalyticsScreen} />
      <Tab.Screen name="Team" component={TeamScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [userToken, setUserToken] = useState(null);

  useEffect(() => {
    // Check if user is logged in
    const bootstrapAsync = async () => {
      try {
        const token = await AuthService.getToken();
        setUserToken(token);
      } catch (e) {
        console.error('Failed to load token:', e);
      } finally {
        setIsLoading(false);
      }
    };

    bootstrapAsync();
  }, []);

  if (isLoading) {
    return <SplashScreen />;
  }

  return (
    <PaperProvider>
      <NavigationContainer>
        <Stack.Navigator>
          {userToken == null ? (
            <Stack.Screen
              name="Login"
              component={LoginScreen}
              options={{ headerShown: false }}
            />
          ) : (
            <Stack.Screen
              name="Main"
              component={MainTabNavigator}
              options={{ headerShown: false }}
            />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
}