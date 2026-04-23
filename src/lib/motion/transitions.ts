import { cubicOut, quintOut } from 'svelte/easing';
import type { FadeParams, FlyParams } from 'svelte/transition';

export const routeTransitionIn: FlyParams = {
	y: 10,
	opacity: 0.96,
	duration: 220,
	easing: cubicOut
};

export const routeTransitionOut: FadeParams = {
	duration: 140,
	easing: cubicOut
};

export const subviewTransitionIn: FlyParams = {
	y: 6,
	opacity: 0.98,
	duration: 180,
	easing: quintOut
};

export const subviewTransitionOut: FadeParams = {
	duration: 120,
	easing: cubicOut
};
