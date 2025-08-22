import type { Meta, StoryObj } from '@storybook/react';
import Button from './Button';

const meta: Meta<typeof Button> = {
  title: 'Design/Button',
  component: Button,
  argTypes: {
    variant: { control: 'select', options: ['primary', 'secondary'] },
  },
};
export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { children: 'Click me' } };
export const Secondary: Story = { args: { variant: 'secondary', children: 'Cancel' } };
