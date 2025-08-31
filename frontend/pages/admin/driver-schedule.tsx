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
            <div className="grid grid-cols-7">
              {calendarDays.map(date => (
                <div
                  key={date.valueOf()}
                  className={`
                    aspect-square min-h-[100px] p-3 border-r border-b last:border-r-0 
                    cursor-pointer transition-colors duration-200
                    ${!isCurrentMonth(date) 
                      ? 'bg-gray-50 text-gray-400' 
                      : 'bg-white hover:bg-blue-50'
                    } 
                    ${isSelected(date) 
                      ? 'bg-blue-100 border-blue-400 ring-2 ring-blue-300' 
                      : ''
                    } 
                    ${isToday(date) && !isSelected(date)
                      ? 'bg-green-50 border-green-300 ring-2 ring-green-200' 
                      : ''
                    }
                  `}
                  onClick={() => setSelectedDate(date)}
                >
                  <div className={`
                    text-base font-semibold mb-2
                    ${isToday(date) ? 'text-green-700' : ''}
                    ${isSelected(date) ? 'text-blue-700' : ''}
                    ${!isCurrentMonth(date) ? 'text-gray-400' : 'text-gray-900'}
                  `}>
                    {date.format('D')}
                  </div>
                  
                  {/* Small indicator for scheduled drivers */}
                  {isCurrentMonth(date) && (
                    <div className="flex items-center justify-center">
                      <div className="w-2 h-2 bg-blue-500 rounded-full opacity-30"></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Selected Date Details */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border">
            <div className="border-b border-gray-200 px-6 py-4 bg-gray-50">
              <div className="flex items-center gap-3">
                <Calendar size={20} className="text-blue-600" />
                <div>
                  <h3 className="font-semibold text-gray-900">
                    {selectedDate.format('dddd')}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {selectedDate.format('MMMM D, YYYY')}
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6">
              {loadingDaily ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-3 text-gray-600">Loading drivers...</p>
                </div>
              ) : (
                <>
                  <div className="mb-4 text-sm text-gray-600">
                    {dailyDrivers?.data?.scheduled_count || 0} drivers scheduled
                  </div>

                  {/* Scheduled Drivers */}
                  <div className="space-y-3 mb-6">
                    <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      Scheduled ({dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).length || 0})
                    </h4>
                    {dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).length === 0 ? (
                      <div className="text-sm text-gray-500 italic">No drivers scheduled</div>
                    ) : (
                      dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).map((driver: Driver) => (
                        <div key={driver.driver_id} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">{driver.driver_name}</div>
                            {driver.phone && <div className="text-sm text-gray-600">{driver.phone}</div>}
                          </div>
                          <button
                            onClick={() => handleRemoveDriver(driver.driver_id)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-1 rounded-md text-sm font-medium transition-colors"
                            disabled={setScheduleMutation.isPending}
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Available Drivers to Add */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                      Available to Schedule
                    </h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {dailyDrivers?.data?.drivers?.filter((d: Driver) => !d.is_scheduled).map((driver: Driver) => (
                        <button
                          key={driver.driver_id}
                          onClick={() => handleAddDriver(driver.driver_id)}
                          className="w-full text-left p-3 hover:bg-blue-50 hover:border-blue-200 rounded-lg border border-gray-200 transition-colors group"
                          disabled={setScheduleMutation.isPending}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Plus size={16} className="text-blue-600 group-hover:text-blue-700" />
                              <div>
                                <div className="font-medium text-gray-900">{driver.driver_name}</div>
                                {driver.phone && <div className="text-sm text-gray-600">{driver.phone}</div>}
                              </div>
                            </div>
                            <span className="text-xs text-blue-600 group-hover:text-blue-700 font-medium">Add</span>
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