import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import { ChevronLeft, ChevronRight, Plus, Calendar, Users } from 'lucide-react';

dayjs.extend(weekOfYear);

interface Driver {
  driver_id: number;
  driver_name: string;
  phone?: string;
  is_scheduled: boolean;
  schedule_type?: string;
  shift_type?: string;
  status?: string;
}

interface WeeklySchedule {
  [date: string]: Array<{
    driver_id: number;
    driver_name: string;
    schedule_type: string;
    shift_type: string;
    status: string;
  }>;
}

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function DriverSchedulePage() {
  const [currentWeekStart, setCurrentWeekStart] = useState(() => {
    return dayjs().startOf('week').add(1, 'day'); // Start week on Monday
  });
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [showCreatePattern, setShowCreatePattern] = useState(false);

  const queryClient = useQueryClient();

  // Fetch weekly schedule
  const { data: weeklySchedule, isLoading: loadingWeekly } = useQuery({
    queryKey: ['weekly-schedule', currentWeekStart.format('YYYY-MM-DD')],
    queryFn: async () => {
      const response = await fetch(`/api/driver-schedule/weekly/${currentWeekStart.format('YYYY-MM-DD')}`);
      if (!response.ok) throw new Error('Failed to fetch weekly schedule');
      return response.json();
    },
  });

  // Fetch daily drivers
  const { data: dailyDrivers, isLoading: loadingDaily } = useQuery({
    queryKey: ['daily-drivers', selectedDate.format('YYYY-MM-DD')],
    queryFn: async () => {
      const response = await fetch(`/api/driver-schedule/drivers/all?target_date=${selectedDate.format('YYYY-MM-DD')}`);
      if (!response.ok) throw new Error('Failed to fetch daily drivers');
      return response.json();
    },
  });

  // Create weekly pattern mutation
  const createPatternMutation = useMutation({
    mutationFn: async (data: {
      driver_id: number;
      weekdays: boolean[];
      pattern_name?: string;
    }) => {
      const response = await fetch('/api/driver-schedule/weekly-pattern', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to create pattern');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weekly-schedule'] });
      queryClient.invalidateQueries({ queryKey: ['daily-drivers'] });
    },
  });

  // Update driver status mutation
  const updateStatusMutation = useMutation({
    mutationFn: async (data: {
      driver_id: number;
      status: string;
      schedule_date?: string;
    }) => {
      const response = await fetch(`/api/driver-schedule/driver/${data.driver_id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: data.status,
          schedule_date: data.schedule_date || selectedDate.format('YYYY-MM-DD'),
        }),
      });
      if (!response.ok) throw new Error('Failed to update status');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-drivers'] });
      queryClient.invalidateQueries({ queryKey: ['weekly-schedule'] });
    },
  });

  const weekDates = Array.from({ length: 7 }, (_, i) => currentWeekStart.add(i, 'day'));

  const goToPreviousWeek = () => setCurrentWeekStart(prev => prev.subtract(1, 'week'));
  const goToNextWeek = () => setCurrentWeekStart(prev => prev.add(1, 'week'));

  const getScheduledDriversForDate = (date: dayjs.Dayjs): Array<{
    driver_id: number;
    driver_name: string;
    schedule_type: string;
    shift_type: string;
    status: string;
  }> => {
    if (!weeklySchedule?.data?.weekly_schedule) return [];
    const dateStr = date.format('YYYY-MM-DD');
    return weeklySchedule.data.weekly_schedule[dateStr] || [];
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SCHEDULED': return 'bg-blue-100 text-blue-800';
      case 'CONFIRMED': return 'bg-green-100 text-green-800';
      case 'CALLED_SICK': return 'bg-yellow-100 text-yellow-800';
      case 'NO_SHOW': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Driver Schedule</h1>
            <p className="text-gray-600 mt-2">Manage driver work schedules and assignments</p>
          </div>
          <button
            onClick={() => setShowCreatePattern(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus size={16} />
            Create Pattern
          </button>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="mb-6 flex items-center justify-between bg-white p-4 rounded-lg shadow">
        <button
          onClick={goToPreviousWeek}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ChevronLeft size={20} />
        </button>
        
        <div className="text-center">
          <h2 className="text-xl font-semibold">
            {currentWeekStart.format('MMM DD')} - {currentWeekStart.add(6, 'day').format('MMM DD, YYYY')}
          </h2>
        </div>

        <button
          onClick={goToNextWeek}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Weekly Calendar */}
      <div className="grid grid-cols-7 gap-4 mb-8">
        {weekDates.map((date, index) => {
          const scheduledDrivers = getScheduledDriversForDate(date);
          const isSelected = date.isSame(selectedDate, 'day');
          const isToday = date.isSame(dayjs(), 'day');

          return (
            <div
              key={date.valueOf()}
              className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all ${
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : isToday
                  ? 'border-green-500'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedDate(date)}
            >
              <div className="text-center mb-3">
                <div className="text-sm font-medium text-gray-600">
                  {WEEKDAYS[index]}
                </div>
                <div className={`text-2xl font-bold ${
                  isToday ? 'text-green-600' : 'text-gray-900'
                }`}>
                  {date.format('DD')}
                </div>
              </div>

              <div className="space-y-2">
                {scheduledDrivers.slice(0, 3).map(driver => (
                  <div
                    key={driver.driver_id}
                    className={`text-xs px-2 py-1 rounded ${getStatusColor(driver.status)}`}
                  >
                    {driver.driver_name}
                  </div>
                ))}
                {scheduledDrivers.length > 3 && (
                  <div className="text-xs text-gray-500">
                    +{scheduledDrivers.length - 3} more
                  </div>
                )}
                {scheduledDrivers.length === 0 && (
                  <div className="text-xs text-gray-400 text-center py-2">
                    No drivers scheduled
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Date Details */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <Calendar size={20} className="text-gray-600" />
            <h3 className="text-lg font-semibold">
              {selectedDate.format('dddd, MMMM DD, YYYY')}
            </h3>
          </div>
        </div>

        <div className="p-6">
          {loadingDaily ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading drivers...</p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Users size={16} className="text-gray-600" />
                  <span className="text-sm font-medium">
                    {dailyDrivers?.data?.scheduled_count || 0} of {dailyDrivers?.data?.total_count || 0} drivers scheduled
                  </span>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {dailyDrivers?.data?.drivers?.map((driver: Driver) => (
                  <div
                    key={driver.driver_id}
                    className={`border rounded-lg p-4 ${
                      driver.is_scheduled 
                        ? 'border-green-200 bg-green-50' 
                        : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900">
                        {driver.driver_name}
                      </h4>
                      <span className={`text-xs px-2 py-1 rounded ${
                        driver.is_scheduled 
                          ? getStatusColor(driver.status || 'SCHEDULED')
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {driver.is_scheduled ? (driver.status || 'SCHEDULED') : 'OFF'}
                      </span>
                    </div>

                    {driver.phone && (
                      <p className="text-sm text-gray-600 mb-2">{driver.phone}</p>
                    )}

                    {driver.is_scheduled && (
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => updateStatusMutation.mutate({
                            driver_id: driver.driver_id,
                            status: 'CONFIRMED'
                          })}
                          className="text-xs bg-green-100 hover:bg-green-200 text-green-800 px-2 py-1 rounded"
                          disabled={updateStatusMutation.isPending}
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => updateStatusMutation.mutate({
                            driver_id: driver.driver_id,
                            status: 'CALLED_SICK'
                          })}
                          className="text-xs bg-yellow-100 hover:bg-yellow-200 text-yellow-800 px-2 py-1 rounded"
                          disabled={updateStatusMutation.isPending}
                        >
                          Sick
                        </button>
                        <button
                          onClick={() => updateStatusMutation.mutate({
                            driver_id: driver.driver_id,
                            status: 'NO_SHOW'
                          })}
                          className="text-xs bg-red-100 hover:bg-red-200 text-red-800 px-2 py-1 rounded"
                          disabled={updateStatusMutation.isPending}
                        >
                          No Show
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Create Pattern Modal */}
      {showCreatePattern && <CreatePatternModal />}
    </div>
  );
}

// Simplified CreatePatternModal component
function CreatePatternModal() {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h3 className="text-lg font-semibold mb-4">Create Weekly Pattern</h3>
        <p className="text-gray-600 mb-4">
          Feature coming soon! For now, use the backend API endpoints to create weekly patterns.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 px-4 rounded"
        >
          Close
        </button>
      </div>
    </div>
  );
}