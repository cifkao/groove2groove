import subprocess
from enum import Enum
from typing import Optional
#TODO Docstrings etc.


class Groove2GrooveModelName(str, Enum):
    """Enum that contains the 4 models (and weights) released with groove2groove"""
    V01_DRUMS = 'v01_drums'
    V01_DRUMS_VEL = 'v01_drums_vel'
    V01 = 'v01'
    V01_VEL = 'v01_vel'
    
    def __str__(self):
        return self.value


def run_groove2groove(content_midi: str, style_midi: str, output_midi: str,
                      temperature: float = 0.4, 
                      model_name: Groove2GrooveModelName = Groove2GrooveModelName.V01_DRUMS, 
                      python_grv2grv_full_link: str = None, 
                      verbose: bool = True):
    """
    A wrapper function for running groove2groove from python as a subprocess with a different virtual environment (python 3.6 with grv2grv dependencies).
    The function gets the relevant groove2groove files and arguments, and generates a new groove2groove output MIDI file.    

    :param content_midi: Path to the content MIDI file (the "sketch", the chords etc.)
    :param style_midi: Path to the style MIDI file (the target "reference").
    :param output_midi: Path where the groove2groove output MIDI file will be saved.
    :param temperature: A float between 0-1 to control the randomness of the generation. Lower values result in less randomness. Default is 0.4.
    :param model_name: The name of the groove2groove model to be used for style transfer.
    :param python_grv2grv_full_link: Optional. Full link to the Python environment matching groove2groove requirements (python 3.6 etc).
    :param verbose: A boolean to control the verbosity of the process. If True, detailed logs will be printed to the terminal.
    """

    python_grv2grv_full_link = 'python' if python_grv2grv_full_link is None else python_grv2grv_full_link 
    grv2grv_command = f"{python_grv2grv_full_link} -m groove2groove.models.roll2seq_style_transfer --logdir './experiments/{model_name}' run-midi \
--sample --softmax-temperature {temperature} '{content_midi}' '{style_midi}' '{output_midi}'"

    if verbose:
        print('running groove2groove:')
        print(grv2grv_command)

    result = subprocess.run(grv2grv_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if verbose:
        # print errors and output
        print(result.stdout.decode())
        print(result.stderr.decode())
        print("goove2groove execution was successful.") if result.returncode == 0 else print("goove2groove execution failed.")
        
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=grv2grv_command,
            output=result.stdout,
            stderr=result.stderr
        )
        

def run_groove2groove_evaluation_script(content_midi: str, style_midi: str, output_midi: str,
                                        analysis_out_path: Optional[str] = None,
                                        temperature: Optional[float] = None, 
                                        model_name: Optional[Groove2GrooveModelName] = None, 
                                        python_grv2grv_full_link: Optional[str] = None, 
                                        verbose: bool = True):

    python_grv2grv_full_link = 'python' if python_grv2grv_full_link is None else python_grv2grv_full_link 
    grv2grv_evaluation_command = f"{python_grv2grv_full_link} -m code.session.grv2grv_eval_script \
--cont_midi_path '{content_midi}' --style_midi_path '{style_midi}' --out_midi_path '{output_midi}'" 
    grv2grv_evaluation_command += f" --analysis_out_path '{analysis_out_path}'" if analysis_out_path is not None else ""
    grv2grv_evaluation_command += f" --model_name {model_name}" if model_name is not None else ""
    grv2grv_evaluation_command += f" --temperature {temperature}" if temperature is not None else ""
    grv2grv_evaluation_command += f" --verbose {verbose}"

    if verbose:
        print('running evaulation (groove2groove metrics):')
        print(grv2grv_evaluation_command)
    
    result = subprocess.run(grv2grv_evaluation_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if verbose:
        # print errors and output
        print(result.stdout.decode())
        print(result.stderr.decode())
        print("goove2groove evaluation execution was successful.") if result.returncode == 0 else print("goove2groove evaluation execution failed.")

    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=grv2grv_evaluation_command,
            output=result.stdout,
            stderr=result.stderr
        )

if __name__=='__main__':
    content_midi = style_midi = 'data/sync/data_for_sync/HitCraft_All_Files_Bank_Thin/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi'
    grv2grv_kwargs = dict(content_midi=content_midi, style_midi=style_midi, output_midi='output.mid', model_name='v01_drums', temperature='0.4', 
                          python_grv2grv_full_link='/home/ubuntu/.conda/envs/groove2groove5/bin/python')
    run_groove2groove(**grv2grv_kwargs)
    run_groove2groove_evaluation_script(**grv2grv_kwargs)

