import pygame
import numpy

def generate_sound(frequency, duration, attack_time=0.01, decay_time=0.1, sound_type='sine'):
    """Generates a pygame sound object with an ADSR-like envelope."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    t = numpy.linspace(0, duration, num_samples, False)

    # Generate wave
    if sound_type == 'sine':
        wave = numpy.sin(frequency * t * 2 * numpy.pi)
    elif sound_type == 'square':
        wave = numpy.sign(numpy.sin(frequency * t * 2 * numpy.pi))
    elif sound_type == 'noise':
        wave = numpy.random.uniform(-1, 1, num_samples)
    else: # Sawtooth
        wave = 2 * (t * frequency - numpy.floor(0.5 + t * frequency))

    # Envelope
    attack_samples = int(sample_rate * attack_time)
    decay_samples = int(sample_rate * decay_time)

    if attack_samples > 0:
        attack = numpy.linspace(0, 1, attack_samples)
        wave[:attack_samples] *= attack
    
    if decay_samples > 0:
        sustain_samples = num_samples - attack_samples
        decay = numpy.exp(-numpy.linspace(0, 5, sustain_samples))
        wave[attack_samples:] *= decay

    # Ensure max amplitude is 1
    wave *= 32767 / numpy.max(numpy.abs(wave))
    wave = wave.astype(numpy.int16)

    # Convert to stereo
    stereo_wave = numpy.array([wave, wave]).T
    
    # Ensure the array is C-contiguous
    stereo_wave_contiguous = numpy.ascontiguousarray(stereo_wave)
    return pygame.sndarray.make_sound(stereo_wave_contiguous)


# --- Create Sound Effects ---
SOUNDS = {
    'laser': generate_sound(1200, 0.2, decay_time=0.2, sound_type='sawtooth'),
    'hit': generate_sound(400, 0.3, decay_time=0.3, sound_type='noise'),
    'death': generate_sound(200, 0.8, decay_time=0.8, sound_type='noise'),
    'move': generate_sound(800, 0.05, decay_time=0.05, sound_type='square')
}
SOUNDS['move'].set_volume(0.5)
