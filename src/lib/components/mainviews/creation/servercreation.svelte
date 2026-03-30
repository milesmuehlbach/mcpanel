<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import Step1 from '$lib/components/mainviews/creation/step1.svelte';

	const totalSteps = 3;
	let step = $state(1);

	function goToStep(nextStep: number) {
		step = Math.min(totalSteps, Math.max(1, nextStep));
	}

	function incrementStep() {
		goToStep(step + 1);
	}
</script>

<div class="flex min-h-screen w-full items-center justify-center bg-background p-4 sm:p-8">
	<Card.Root class="w-full max-w-2xl">
		<Card.Content class="min-h-56">
			{#if step === 1}
				<Step1 {incrementStep} />
			{:else if step === 2}
				<div class="space-y-2">
					<h2 class="text-xl font-semibold">Server Configuration</h2>
					<p class="text-muted-foreground">Customize server settings for your environment.</p>
				</div>
			{:else}
				<div class="space-y-2">
					<h2 class="text-xl font-semibold">Review & Launch</h2>
					<p class="text-muted-foreground">
						Review your selections and create the server when ready.
					</p>
				</div>
			{/if}
		</Card.Content>
	</Card.Root>
</div>
