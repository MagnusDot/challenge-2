<template>
  <div class="flex flex-col gap-2 animate-fade-in-up" :style="{ animationDelay: `${index * 0.1}s` }">
    <label :for="id" class="text-sm font-medium text-zinc-400 group-hover:text-blue-400 transition-colors duration-300">{{ label }}</label>
    <select
      :id="id"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
      class="px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300 cursor-pointer appearance-none bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMUw2IDZMMTEgMSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjEuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+')] bg-[length:12px_8px] bg-[right_12px_center] bg-no-repeat pr-10 hover:bg-zinc-700 hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/20 transform hover:scale-105"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="option.value" :value="option.value" class="bg-zinc-800">
        {{ option.label }}
      </option>
    </select>
  </div>
</template>

<script>
export default {
  name: 'FilterGroup',
  props: {
    id: {
      type: String,
      required: true
    },
    label: {
      type: String,
      required: true
    },
    modelValue: {
      type: String,
      default: ''
    },
    options: {
      type: Array,
      required: true
    },
    placeholder: {
      type: String,
      default: 'All'
    },
    index: {
      type: Number,
      default: 0
    }
  },
  emits: ['update:modelValue']
};
</script>
