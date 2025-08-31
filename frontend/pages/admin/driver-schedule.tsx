import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { ChevronLeft, ChevronRight, Calendar, Plus } from 'lucide-react';

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

  // Fetch daily drivers for selected date - use simple /drivers endpoint that works
  const { data: dailyDrivers, isLoading: loadingDaily } = useQuery({
    queryKey: ['daily-drivers', selectedDate.format('YYYY-MM-DD')],
    queryFn: async () => {
      const response = await fetch(`/_api/drivers`);
      if (!response.ok) throw new Error('Failed to fetch drivers');
      const drivers = await response.json();
      
      // Transform to match expected format
      return {
        data: {
          drivers: drivers.map((driver: any) => ({
            driver_id: driver.id,
            driver_name: driver.name || 'Unknown Driver',
            phone: driver.phone,
            is_scheduled: false, // All drivers start as unscheduled
            schedule_type: null,
            shift_type: null,
            status: null
          })),
          scheduled_count: 0,
          total_count: drivers.length
        }
      };
    },
  });

  // Set daily schedule mutation
  const setScheduleMutation = useMutation({
    mutationFn: async (data: {
      driver_id: number;
      schedule_date: string;
      is_scheduled: boolean;
    }) => {
      const response = await fetch('/_api/driver-schedule/daily-override', {
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
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 'bold', color: '#111827', marginBottom: '8px' }}>
          Driver Schedule
        </h1>
        <p style={{ color: '#6B7280' }}>
          Manage daily driver schedules
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '32px' }}>
        {/* Month Calendar */}
        <div>
          <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #E5E7EB' }}>
            {/* Month Navigation */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              padding: '16px 24px', 
              borderBottom: '1px solid #E5E7EB' 
            }}>
              <button
                onClick={goToPreviousMonth}
                style={{ 
                  padding: '8px', 
                  borderRadius: '6px', 
                  border: 'none', 
                  backgroundColor: 'transparent',
                  cursor: 'pointer'
                }}
                onMouseOver={(e) => (e.target as HTMLElement).style.backgroundColor = '#F3F4F6'}
                onMouseOut={(e) => (e.target as HTMLElement).style.backgroundColor = 'transparent'}
              >
                <ChevronLeft size={20} />
              </button>
              
              <h2 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>
                {currentMonth.format('MMMM YYYY')}
              </h2>

              <button
                onClick={goToNextMonth}
                style={{ 
                  padding: '8px', 
                  borderRadius: '6px', 
                  border: 'none', 
                  backgroundColor: 'transparent',
                  cursor: 'pointer'
                }}
                onMouseOver={(e) => (e.target as HTMLElement).style.backgroundColor = '#F3F4F6'}
                onMouseOut={(e) => (e.target as HTMLElement).style.backgroundColor = 'transparent'}
              >
                <ChevronRight size={20} />
              </button>
            </div>

            {/* Weekday Headers */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(7, 1fr)',
              borderBottom: '1px solid #E5E7EB'
            }}>
              {WEEKDAYS.map(day => (
                <div 
                  key={day} 
                  style={{ 
                    padding: '12px', 
                    textAlign: 'center', 
                    fontSize: '14px', 
                    fontWeight: '500', 
                    color: '#6B7280',
                    borderRight: '1px solid #E5E7EB'
                  }}
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Calendar Grid */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(7, 1fr)'
            }}>
              {calendarDays.map(date => {
                const isCurrentMonthDate = isCurrentMonth(date);
                const isTodayDate = isToday(date);
                const isSelectedDate = isSelected(date);

                return (
                  <div
                    key={date.valueOf()}
                    onClick={() => setSelectedDate(date)}
                    style={{
                      minHeight: '80px',
                      padding: '12px',
                      borderRight: '1px solid #E5E7EB',
                      borderBottom: '1px solid #E5E7EB',
                      cursor: 'pointer',
                      backgroundColor: !isCurrentMonthDate 
                        ? '#F9FAFB' 
                        : isSelectedDate 
                        ? '#EBF8FF' 
                        : isTodayDate 
                        ? '#F0FDF4'
                        : 'white',
                      color: !isCurrentMonthDate ? '#9CA3AF' : '#111827',
                      border: isSelectedDate ? '2px solid #3B82F6' : isTodayDate ? '2px solid #10B981' : '1px solid #E5E7EB',
                      transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => {
                      if (isCurrentMonthDate && !isSelectedDate) {
                        (e.target as HTMLElement).style.backgroundColor = '#F3F4F6';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (isCurrentMonthDate && !isSelectedDate) {
                        (e.target as HTMLElement).style.backgroundColor = isTodayDate ? '#F0FDF4' : 'white';
                      }
                    }}
                  >
                    <div style={{ 
                      fontSize: '16px', 
                      fontWeight: '600', 
                      marginBottom: '4px',
                      color: isTodayDate ? '#059669' : isSelectedDate ? '#1D4ED8' : 'inherit'
                    }}>
                      {date.format('D')}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Selected Date Details */}
        <div>
          <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #E5E7EB' }}>
            <div style={{ 
              padding: '16px 24px', 
              borderBottom: '1px solid #E5E7EB',
              backgroundColor: '#F9FAFB'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Calendar size={20} style={{ color: '#3B82F6' }} />
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', margin: 0, color: '#111827' }}>
                    {selectedDate.format('dddd')}
                  </h3>
                  <p style={{ fontSize: '14px', color: '#6B7280', margin: 0 }}>
                    {selectedDate.format('MMMM D, YYYY')}
                  </p>
                </div>
              </div>
            </div>

            <div style={{ padding: '24px' }}>
              {loadingDaily ? (
                <div style={{ textAlign: 'center', padding: '32px 0' }}>
                  <div style={{ 
                    width: '32px', 
                    height: '32px', 
                    border: '2px solid #E5E7EB', 
                    borderTop: '2px solid #3B82F6',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 12px'
                  }}></div>
                  <p style={{ color: '#6B7280', margin: 0 }}>Loading drivers...</p>
                </div>
              ) : (
                <>
                  <div style={{ marginBottom: '16px', fontSize: '14px', color: '#6B7280' }}>
                    {dailyDrivers?.data?.scheduled_count || 0} drivers scheduled
                  </div>

                  {/* Scheduled Drivers */}
                  <div style={{ marginBottom: '24px' }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '12px', height: '12px', backgroundColor: '#10B981', borderRadius: '50%' }}></div>
                      Scheduled ({dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).length || 0})
                    </h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).length === 0 ? (
                        <div style={{ fontSize: '14px', color: '#9CA3AF', fontStyle: 'italic' }}>No drivers scheduled</div>
                      ) : (
                        dailyDrivers?.data?.drivers?.filter((d: Driver) => d.is_scheduled).map((driver: Driver) => (
                          <div key={driver.driver_id} style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '12px',
                            backgroundColor: '#ECFDF5',
                            border: '1px solid #D1FAE5',
                            borderRadius: '8px'
                          }}>
                            <div>
                              <div style={{ fontWeight: '500', color: '#111827' }}>{driver.driver_name}</div>
                              {driver.phone && <div style={{ fontSize: '14px', color: '#6B7280' }}>{driver.phone}</div>}
                            </div>
                            <button
                              onClick={() => handleRemoveDriver(driver.driver_id)}
                              disabled={setScheduleMutation.isPending}
                              style={{
                                color: '#DC2626',
                                backgroundColor: 'transparent',
                                border: 'none',
                                padding: '6px 12px',
                                borderRadius: '6px',
                                fontSize: '14px',
                                fontWeight: '500',
                                cursor: 'pointer'
                              }}
                              onMouseOver={(e) => {
                                (e.target as HTMLElement).style.backgroundColor = '#FEF2F2';
                                (e.target as HTMLElement).style.color = '#B91C1C';
                              }}
                              onMouseOut={(e) => {
                                (e.target as HTMLElement).style.backgroundColor = 'transparent';
                                (e.target as HTMLElement).style.color = '#DC2626';
                              }}
                            >
                              Remove
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Available Drivers */}
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#374151', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '12px', height: '12px', backgroundColor: '#9CA3AF', borderRadius: '50%' }}></div>
                      Available to Schedule
                    </h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                      {dailyDrivers?.data?.drivers?.filter((d: Driver) => !d.is_scheduled).map((driver: Driver) => (
                        <button
                          key={driver.driver_id}
                          onClick={() => handleAddDriver(driver.driver_id)}
                          disabled={setScheduleMutation.isPending}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '12px',
                            backgroundColor: 'white',
                            border: '1px solid #E5E7EB',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onMouseOver={(e) => {
                            (e.target as HTMLElement).style.backgroundColor = '#EBF8FF';
                            (e.target as HTMLElement).style.borderColor = '#BFDBFE';
                          }}
                          onMouseOut={(e) => {
                            (e.target as HTMLElement).style.backgroundColor = 'white';
                            (e.target as HTMLElement).style.borderColor = '#E5E7EB';
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <Plus size={16} style={{ color: '#3B82F6' }} />
                            <div>
                              <div style={{ fontWeight: '500', color: '#111827' }}>{driver.driver_name}</div>
                              {driver.phone && <div style={{ fontSize: '14px', color: '#6B7280' }}>{driver.phone}</div>}
                            </div>
                          </div>
                          <span style={{ fontSize: '12px', color: '#3B82F6', fontWeight: '500' }}>Add</span>
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

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}