import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { ChevronLeft, ChevronRight, Calendar, Users, Plus } from 'lucide-react';

interface Driver {
  driver_id: number;
  driver_name: string;
  phone?: string;
  is_scheduled: boolean;
  schedule_type?: string;
  shift_type?: string;
  status?: string;
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function DriverSchedulePage() {
  const [currentMonth, setCurrentMonth] = useState(dayjs());
  const [selectedDate, setSelectedDate] = useState(dayjs());

  const queryClient = useQueryClient();

  // Fetch daily drivers for selected date
  const { data: dailyDrivers, isLoading: loadingDaily } = useQuery({
    queryKey: ['daily-drivers', selectedDate.format('YYYY-MM-DD')],
    queryFn: async () => {
      const response = await fetch(`/api/driver-schedule/drivers/all?target_date=${selectedDate.format('YYYY-MM-DD')}`);
      if (!response.ok) throw new Error('Failed to fetch daily drivers');
      return response.json();
    },
  });

  // Get all drivers for dropdown
  const { data: allDrivers } = useQuery({
    queryKey: ['all-drivers'],
    queryFn: async () => {
      const response = await fetch('/api/drivers');
      if (!response.ok) throw new Error('Failed to fetch drivers');
      return response.json();
    },
  });

  // Set daily schedule mutation
  const setScheduleMutation = useMutation({
    mutationFn: async (data: {
      driver_id: number;
      schedule_date: string;
      is_scheduled: boolean;
    }) => {
      const response = await fetch('/api/driver-schedule/daily-override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          driver_id: data.driver_id,
          schedule_date: data.schedule_date,
          is_scheduled: data.is_scheduled,
          shift_type: 'FULL_DAY'
        }),
      });
      if (!response.ok) throw new Error('Failed to set schedule');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-drivers'] });
    },
  });

  // Generate calendar days
  const startOfMonth = currentMonth.startOf('month');
  const endOfMonth = currentMonth.endOf('month');
  const startOfCalendar = startOfMonth.startOf('week');
  const endOfCalendar = endOfMonth.endOf('week');
  
  const calendarDays = [];
  let currentDay = startOfCalendar;
  
  while (currentDay.isBefore(endOfCalendar) || currentDay.isSame(endOfCalendar, 'day')) {
    calendarDays.push(currentDay);
    currentDay = currentDay.add(1, 'day');
  }

  const goToPreviousMonth = () => setCurrentMonth(prev => prev.subtract(1, 'month'));
  const goToNextMonth = () => setCurrentMonth(prev => prev.add(1, 'month'));

  const isCurrentMonth = (date: dayjs.Dayjs) => date.isSame(currentMonth, 'month');
  const isToday = (date: dayjs.Dayjs) => date.isSame(dayjs(), 'day');
  const isSelected = (date: dayjs.Dayjs) => date.isSame(selectedDate, 'day');

  const handleAddDriver = (driverId: number) => {
    setScheduleMutation.mutate({
      driver_id: driverId,
      schedule_date: selectedDate.format('YYYY-MM-DD'),
      is_scheduled: true
    });
  };

  const handleRemoveDriver = (driverId: number) => {
    setScheduleMutation.mutate({
      driver_id: driverId,
      schedule_date: selectedDate.format('YYYY-MM-DD'),
      is_scheduled: false
    });
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Driver Schedule</h1>
            <p className="text-gray-600 mt-2">Manage daily driver schedules</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Month Calendar */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            {/* Month Navigation */}
            <div className="flex items-center justify-between p-4 border-b">
              <button
                onClick={goToPreviousMonth}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <ChevronLeft size={20} />
              </button>
              
              <h2 className="text-xl font-semibold">
                {currentMonth.format('MMMM YYYY')}
              </h2>

              <button
                onClick={goToNextMonth}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <ChevronRight size={20} />
              </button>
            </div>

            {/* Weekday Headers */}
            <div className="grid grid-cols-7 gap-0 border-b">
              {WEEKDAYS.map(day => (
                <div key={day} className="p-3 text-center text-sm font-medium text-gray-600 border-r last:border-r-0">
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-0">
              {calendarDays.map(date => (
                <div
                  key={date.valueOf()}
                  className={`min-h-[80px] p-2 border-r border-b last:border-r-0 cursor-pointer hover:bg-gray-50 ${
                    !isCurrentMonth(date) ? 'bg-gray-50 text-gray-400' : ''
                  } ${
                    isSelected(date) ? 'bg-blue-50 border-blue-300' : ''
                  } ${
                    isToday(date) ? 'bg-green-50 border-green-300' : ''
                  }`}
                  onClick={() => setSelectedDate(date)}
                >
                  <div className={`text-sm font-medium mb-1 ${
                    isToday(date) ? 'text-green-600' : ''
                  }`}>
                    {date.format('D')}
                  </div>
                  
                  {/* Show driver count if current month */}
                  {isCurrentMonth(date) && (
                    <div className="text-xs text-gray-500">
                      {/* This would show scheduled driver count - simplified for now */}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Selected Date Details */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200 px-4 py-3">
              <div className="flex items-center gap-2">
                <Calendar size={18} className="text-gray-600" />
                <h3 className="font-semibold">
                  {selectedDate.format('MMM D, YYYY')}
                </h3>
              </div>
            </div>

            <div className="p-4">
              {loadingDaily ? (
                <div className="text-center py-4">
                  <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  <p className="mt-2 text-sm text-gray-600">Loading...</p>
                </div>
              ) : (
                <>
                  <div className="mb-4 text-sm text-gray-600">
                    {dailyDrivers?.data?.scheduled_count || 0} drivers scheduled
                  </div>

                  {/* Scheduled Drivers */}
                  <div className="space-y-2 mb-4">
                    {dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).map((driver: Driver) => (
                      <div key={driver.driver_id} className="flex items-center justify-between p-2 bg-green-50 rounded border border-green-200">
                        <div>
                          <div className="font-medium text-sm">{driver.driver_name}</div>
                          {driver.phone && <div className="text-xs text-gray-600">{driver.phone}</div>}
                        </div>
                        <button
                          onClick={() => handleRemoveDriver(driver.driver_id)}
                          className="text-red-600 hover:text-red-800 text-xs"
                          disabled={setScheduleMutation.isPending}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Available Drivers to Add */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Add Drivers:</h4>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {dailyDrivers?.data?.drivers?.filter((d: Driver) => !d.is_scheduled).map((driver: Driver) => (
                        <button
                          key={driver.driver_id}
                          onClick={() => handleAddDriver(driver.driver_id)}
                          className="w-full text-left p-2 hover:bg-blue-50 rounded text-sm border border-gray-200"
                          disabled={setScheduleMutation.isPending}
                        >
                          <div className="flex items-center gap-2">
                            <Plus size={14} className="text-blue-600" />
                            <div>
                              <div className="font-medium">{driver.driver_name}</div>
                              {driver.phone && <div className="text-xs text-gray-600">{driver.phone}</div>}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}