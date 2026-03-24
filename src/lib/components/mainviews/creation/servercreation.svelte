<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Progress } from '$lib/components/ui/progress';

	const totalSteps = 3;
	let step = $state(1);

	const progressValue = $derived((step / totalSteps) * 100);

	function goToStep(nextStep: number) {
		step = Math.min(totalSteps, Math.max(1, nextStep));
	}

	function incrementStep() {
		goToStep(step + 1);
	}

	function decrementStep() {
		goToStep(step - 1);
	}
</script>

<div class="flex min-h-screen w-full items-center justify-center bg-background p-4 sm:p-8">
	<Card.Root class="w-full max-w-2xl">
		<Card.Header class="gap-4">
			<div>
				<Card.Title>Create New Server</Card.Title>
				<Card.Description>Step {step} of {totalSteps}</Card.Description>
			</div>
		</Card.Header>

		<Card.Content class="min-h-56 py-6">
			{#if step === 1}
				<h1>step 1</h1>
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

		<Card.Footer class="flex flex-col items-stretch gap-4 border-t pt-6">
			<div class="flex items-center justify-between gap-4">
				<Progress value={progressValue} max={100} class="h-2 w-full" />
			</div>
			<div class="flex justify-between">
				<Button type="button" variant="outline" onclick={decrementStep} disabled={step === 1}
					>Back</Button
				>
				<Button type="button" onclick={incrementStep} disabled={step === totalSteps}>Next</Button>
			</div>
		</Card.Footer>
	</Card.Root>
</div>
