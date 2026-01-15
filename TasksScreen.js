import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { Card, Title, Paragraph, Button, FAB, Searchbar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import DateTimePicker from '@react-native-community/datetimepicker';
import { TaskService } from '../services/TaskService';

const TasksScreen = ({ navigation }) => {
  const [tasks, setTasks] = useState([]);
  const [filteredTasks, setFilteredTasks] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // all, today, upcoming, completed
  const [showDatePicker, setShowDatePicker] = useState(false);

  useEffect(() => {
    loadTasks();
  }, [filter]);

  useEffect(() => {
    filterTasks();
  }, [searchQuery, tasks]);

  const loadTasks = async () => {
    try {
      setRefreshing(true);
      const fetchedTasks = await TaskService.getTasks(filter);
      setTasks(fetchedTasks);
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось загрузить задачи');
    } finally {
      setRefreshing(false);
    }
  };

  const filterTasks = () => {
    let filtered = tasks;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(task =>
        task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredTasks(filtered);
  };

  const toggleTaskCompletion = async (taskId, isCompleted) => {
    try {
      await TaskService.updateTask(taskId, { is_completed: !isCompleted });
      loadTasks(); // Reload tasks
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось обновить задачу');
    }
  };

  const deleteTask = async (taskId) => {
    Alert.alert(
      'Удаление задачи',
      'Вы уверены, что хотите удалить эту задачу?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Удалить',
          style: 'destructive',
          onPress: async () => {
            try {
              await TaskService.deleteTask(taskId);
              loadTasks();
            } catch (error) {
              Alert.alert('Ошибка', 'Не удалось удалить задачу');
            }
          },
        },
      ]
    );
  };

  const renderTaskItem = ({ item }) => (
    <Card style={styles.taskCard}>
      <Card.Content>
        <View style={styles.taskHeader}>
          <TouchableOpacity onPress={() => toggleTaskCompletion(item.id, item.is_completed)}>
            <Icon
              name={item.is_completed ? 'check-circle' : 'radio-button-unchecked'}
              size={24}
              color={item.is_completed ? '#4CAF50' : '#9E9E9E'}
            />
          </TouchableOpacity>
          <View style={styles.taskInfo}>
            <Title style={[styles.taskTitle, item.is_completed && styles.completedTask]}>
              {item.title}
            </Title>
            {item.description && (
              <Paragraph numberOfLines={2}>{item.description}</Paragraph>
            )}
            <View style={styles.taskMeta}>
              <Text style={styles.taskDate}>
                <Icon name="access-time" size={14} /> {formatDate(item.due_date)}
              </Text>
              {item.priority && (
                <Text style={[styles.priority, getPriorityStyle(item.priority)]}>
                  Приоритет: {item.priority}
                </Text>
              )}
              {item.category && (
                <Text style={styles.category}>{item.category}</Text>
              )}
            </View>
          </View>
        </View>
      </Card.Content>
      <Card.Actions>
        <Button onPress={() => navigation.navigate('TaskEdit', { taskId: item.id })}>
          Редактировать
        </Button>
        <Button onPress={() => deleteTask(item.id)} color="#F44336">
          Удалить
        </Button>
      </Card.Actions>
    </Card>
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getPriorityStyle = (priority) => {
    switch (priority) {
      case 1: return { color: '#F44336', fontWeight: 'bold' };
      case 2: return { color: '#FF9800' };
      case 3: return { color: '#4CAF50' };
      default: return { color: '#9E9E9E' };
    }
  };

  return (
    <View style={styles.container}>
      <Searchbar
        placeholder="Поиск задач..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={styles.searchBar}
      />

      <View style={styles.filterContainer}>
        {['all', 'today', 'upcoming', 'completed'].map((filterName) => (
          <Button
            key={filterName}
            mode={filter === filterName ? 'contained' : 'outlined'}
            onPress={() => setFilter(filterName)}
            style={styles.filterButton}
          >
            {getFilterLabel(filterName)}
          </Button>
        ))}
      </View>

      <FlatList
        data={filteredTasks}
        renderItem={renderTaskItem}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadTasks} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Icon name="assignment" size={64} color="#BDBDBD" />
            <Text style={styles.emptyText}>Задачи не найдены</Text>
          </View>
        }
      />

      <FAB
        style={styles.fab}
        icon="add"
        onPress={() => navigation.navigate('TaskCreate')}
      />

      {showDatePicker && (
        <DateTimePicker
          value={new Date()}
          mode="datetime"
          display="default"
          onChange={(event, date) => {
            setShowDatePicker(false);
            if (date) {
              // Handle date selection
            }
          }}
        />
      )}
    </View>
  );
};

const getFilterLabel = (filter) => {
  switch (filter) {
    case 'all': return 'Все';
    case 'today': return 'Сегодня';
    case 'upcoming': return 'Предстоящие';
    case 'completed': return 'Выполненные';
    default: return filter;
  }
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchBar: {
    margin: 10,
    elevation: 2,
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 10,
    paddingBottom: 10,
  },
  filterButton: {
    marginRight: 5,
    flex: 1,
  },
  taskCard: {
    marginHorizontal: 10,
    marginVertical: 5,
    elevation: 3,
  },
  taskHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  taskInfo: {
    flex: 1,
    marginLeft: 10,
  },
  taskTitle: {
    fontSize: 16,
    marginBottom: 5,
  },
  completedTask: {
    textDecorationLine: 'line-through',
    color: '#9E9E9E',
  },
  taskMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 5,
  },
  taskDate: {
    fontSize: 12,
    color: '#757575',
    marginRight: 10,
  },
  priority: {
    fontSize: 12,
    marginRight: 10,
  },
  category: {
    fontSize: 12,
    color: '#2196F3',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 50,
  },
  emptyText: {
    fontSize: 18,
    color: '#757575',
    marginTop: 16,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: '#3498db',
  },
});

export default TasksScreen;